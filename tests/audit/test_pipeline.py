import logging
import uuid
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from auditor.audit.pipeline import claim_next_run, process_run
from auditor.db import models as db
from auditor.enums import AnswerStatus, ClaimLabel, ErrorType, RunStatus
from auditor.llm.errors import (
    PermanentProviderError,
    ProviderConfigError,
    ProviderTimeoutError,
    TransientProviderError,
)
from auditor.metrics import estimate_cost_usd, wilson_interval

from .fakes import FakeVerifier, Writers, create_run, make_settings

Factory = sessionmaker[Session]

TWO_BY_TWO = {
    "category": "earbuds",
    "prompt_ids": ["p01", "p02"],
    "answer_providers": ["gemini", "openai"],
    "repeats": 2,
}
ONE_GEMINI_PROMPT = {
    "category": "earbuds",
    "prompt_ids": ["p01"],
    "answer_providers": ["gemini"],
    "repeats": 2,
}


class Harness:
    """Runs process_run with fake writers and a fake verifier, recording sleeps."""

    def __init__(self, factory: Factory) -> None:
        self.factory = factory
        self.delays: list[float] = []
        self.writers = Writers()
        self.verifier = FakeVerifier()

    def run(self, run_id: uuid.UUID, settings=None, **options: Any) -> RunStatus:
        options.setdefault("answer_client_for", self.writers)
        options.setdefault("verifier_client", self.verifier)
        return process_run(
            run_id,
            session_factory=self.factory,
            settings=settings or make_settings(),
            sleep=self.delays.append,
            rand=lambda: 0.0,
            **options,
        )

    def get_run(self, run_id: uuid.UUID) -> db.AuditRun:
        with self.factory() as session:
            return session.get(db.AuditRun, run_id)

    def answers(self, run_id: uuid.UUID) -> list[db.Answer]:
        with self.factory() as session:
            return list(
                session.scalars(
                    select(db.Answer)
                    .where(db.Answer.run_id == run_id)
                    .order_by(db.Answer.prompt_id, db.Answer.model, db.Answer.repeat_index)
                )
            )


@pytest.fixture
def harness(seeded: Factory) -> Harness:
    return Harness(seeded)


def inclusion(metrics: dict, brand_id: str, model: str | None) -> dict:
    (row,) = [r for r in metrics["inclusion"] if (r["brand_id"], r["model"]) == (brand_id, model)]
    return row


def test_full_run_computes_metrics_from_stored_rows(harness: Harness) -> None:
    run_id = create_run(harness.factory, TWO_BY_TWO)
    assert claim_next_run(harness.factory) == run_id
    settings = make_settings(input_token_price_per_million="1", output_token_price_per_million="4")

    assert harness.run(run_id, settings) == RunStatus.COMPLETED

    run = harness.get_run(run_id)
    metrics = run.metrics
    assert run.status == RunStatus.COMPLETED
    assert run.finished_at is not None
    # 2 prompts x 2 providers x 2 repeats; each answer: 1 writer call + 2 verifier turns.
    assert metrics["answers"]["total"] == 8
    assert metrics["answers"]["verified"] == 8
    assert metrics["model_calls"] == {"used": 8 + 8 * 2, "max": 500}

    # Gemini answers name Kovalt, OpenAI answers do not.
    assert inclusion(metrics, "kovalt", "gemini-answer") == {
        "brand_id": "kovalt",
        "provider": "gemini",
        "model": "gemini-answer",
        "k": 4,
        "n": 4,
        "rate": 1.0,
        "ci_low": wilson_interval(4, 4)[0],
        "ci_high": wilson_interval(4, 4)[1],
    }
    assert inclusion(metrics, "kovalt", "openai-answer")["k"] == 0
    combined = inclusion(metrics, "kovalt", None)
    assert (combined["k"], combined["n"], combined["rate"]) == (4, 8, 0.5)
    assert (combined["ci_low"], combined["ci_high"]) == wilson_interval(4, 8)
    assert inclusion(metrics, "zentro", None)["k"] == 8
    assert inclusion(metrics, "tavora", None)["k"] == 0

    assert metrics["claims"]["total"] == 4
    assert metrics["claims"]["labels"]["contradicted"] == {"count": 4, "share": 1.0}
    assert metrics["claims"]["labels"]["supported"] == {"count": 0, "share": 0.0}
    assert metrics["errors_by_type"] == {}

    # Writer: 10 in / 40 out per answer. Verifier: 2 turns x (50 in / 10 out) per answer.
    assert metrics["tokens"]["generation"] == {"input": 80, "output": 320, "thinking": None}
    assert metrics["tokens"]["verification"] == {"input": 800, "output": 160, "thinking": None}
    assert metrics["tokens"]["total"] == {"input": 880, "output": 480, "thinking": None}
    assert metrics["cost_usd"] == float(estimate_cost_usd(880, 480, Decimal(1), Decimal(4)))


def test_claims_offsets_and_review_items_are_saved(harness: Harness) -> None:
    run_id = create_run(harness.factory, ONE_GEMINI_PROMPT)
    harness.run(run_id)

    with harness.factory() as session:
        claims = session.scalars(select(db.Claim)).all()
        reviews = session.scalars(select(db.ReviewItem)).all()
        texts = {a.id: a.text for a in session.scalars(select(db.Answer))}
    assert len(claims) == 2
    for claim in claims:
        assert texts[claim.answer_id][claim.start_offset : claim.end_offset] == claim.quote
        assert claim.label == ClaimLabel.CONTRADICTED
    assert {review.claim_id for review in reviews} == {claim.id for claim in claims}


def test_cost_is_null_without_prices(harness: Harness) -> None:
    run_id = create_run(harness.factory, ONE_GEMINI_PROMPT)
    harness.run(run_id)
    assert harness.get_run(run_id).metrics["cost_usd"] is None


def test_collection_retries_transient_errors(harness: Harness) -> None:
    harness.writers = Writers(gemini=[TransientProviderError("429"), ProviderTimeoutError("slow")])
    run_id = create_run(harness.factory, dict(ONE_GEMINI_PROMPT, repeats=1))

    assert harness.run(run_id) == RunStatus.COMPLETED
    assert harness.delays == [1.0, 2.0]
    (answer,) = harness.answers(run_id)
    assert answer.status == AnswerStatus.VERIFIED
    # Retries are attempts of one call: the budget counts 1 collection call.
    assert harness.get_run(run_id).model_calls == 1 + 2


def test_a_failed_answer_is_recorded_and_the_run_continues(harness: Harness) -> None:
    harness.writers = Writers(gemini=[PermanentProviderError("400 bad request")])
    run_id = create_run(harness.factory, ONE_GEMINI_PROMPT)

    assert harness.run(run_id) == RunStatus.COMPLETED
    failed, verified = harness.answers(run_id)
    assert failed.status == AnswerStatus.GENERATION_FAILED
    assert failed.error_type == ErrorType.PROVIDER
    assert verified.status == AnswerStatus.VERIFIED
    metrics = harness.get_run(run_id).metrics
    assert metrics["errors_by_type"] == {"provider": 1}
    assert inclusion(metrics, "zentro", None)["n"] == 1  # only answers with text count


def test_budget_exhausted_before_verification_gives_partial(harness: Harness) -> None:
    run_id = create_run(harness.factory, dict(ONE_GEMINI_PROMPT, max_model_calls=5))

    # 2 collection calls fit; verifying needs a reservation of 4 more, and 2 + 4 > 5.
    assert harness.run(run_id) == RunStatus.PARTIAL
    run = harness.get_run(run_id)
    assert run.model_calls == 2
    assert run.metrics["answers"]["pending"] == 2
    assert harness.verifier.calls == 0


def test_unused_turns_are_refunded(harness: Harness) -> None:
    run_id = create_run(harness.factory, dict(ONE_GEMINI_PROMPT, max_model_calls=7))

    # Collect 2 (used 2). Verify #1: reserve 4 (6), use 2, refund 2 (4).
    # Verify #2 would need 4 + 4 = 8 > 7, so the run stops as partial.
    assert harness.run(run_id) == RunStatus.PARTIAL
    statuses = [answer.status for answer in harness.answers(run_id)]
    assert sorted(statuses) == [AnswerStatus.PENDING, AnswerStatus.VERIFIED]
    assert harness.get_run(run_id).model_calls == 4


def test_a_stopped_run_resumes_without_repeating_collection(harness: Harness) -> None:
    run_id = create_run(harness.factory, TWO_BY_TWO)
    first = harness.writers

    status = harness.run(run_id, should_stop=lambda: first.total_calls >= 3)

    assert status == RunStatus.QUEUED  # handed back to the queue
    assert len(harness.answers(run_id)) == 3

    second = Writers()
    assert harness.run(run_id, answer_client_for=second) == RunStatus.COMPLETED
    assert second.total_calls == 5  # only the missing answers
    answers = harness.answers(run_id)
    assert len(answers) == 8
    slots = {(a.prompt_id, a.model, a.repeat_index) for a in answers}
    assert len(slots) == 8


def test_resume_after_a_failure_during_verification_makes_zero_collection_calls(
    harness: Harness,
) -> None:
    run_id = create_run(harness.factory, ONE_GEMINI_PROMPT)

    class BrokenVerifier(FakeVerifier):
        def generate(self, **kwargs):
            raise ProviderConfigError("401 bad key")

    assert harness.run(run_id, verifier_client=BrokenVerifier()) == RunStatus.FAILED
    assert [a.status for a in harness.answers(run_id)] == [AnswerStatus.PENDING] * 2

    second = Writers()
    assert harness.run(run_id, answer_client_for=second) == RunStatus.COMPLETED
    assert second.total_calls == 0
    assert [a.status for a in harness.answers(run_id)] == [AnswerStatus.VERIFIED] * 2


def test_unknown_category_is_a_data_error(harness: Harness) -> None:
    run_id = create_run(harness.factory, dict(ONE_GEMINI_PROMPT, category="toasters"))

    assert harness.run(run_id) == RunStatus.FAILED
    assert harness.get_run(run_id).failure_reason == "data: no prompts in category 'toasters'"
    assert harness.writers.total_calls == 0


def test_prompt_outside_the_category_is_a_data_error(harness: Harness) -> None:
    run_id = create_run(harness.factory, dict(ONE_GEMINI_PROMPT, prompt_ids=["p01", "p99"]))
    harness.run(run_id)
    assert harness.get_run(run_id).failure_reason == (
        "data: prompt IDs not in category 'earbuds': ['p99']"
    )


def test_invalid_stored_config_is_a_data_error(harness: Harness) -> None:
    run_id = create_run(harness.factory, {"category": "earbuds"})
    harness.run(run_id)
    assert harness.get_run(run_id).failure_reason.startswith("data: invalid run config")


def test_missing_answer_model_is_a_config_error_without_traceback(
    harness: Harness, caplog: pytest.LogCaptureFixture
) -> None:
    run_id = create_run(harness.factory, ONE_GEMINI_PROMPT)
    settings = make_settings(gemini_answer_model="")

    with caplog.at_level(logging.ERROR):
        status = harness.run(run_id, settings, answer_client_for=None)

    assert status == RunStatus.FAILED
    assert harness.get_run(run_id).failure_reason == (
        "config: no answer model given: set GEMINI_ANSWER_MODEL"
    )
    assert [record.exc_info for record in caplog.records] == [None]
    assert harness.answers(run_id) == []


def test_missing_verifier_is_a_config_error_before_any_call(harness: Harness) -> None:
    run_id = create_run(harness.factory, ONE_GEMINI_PROMPT)
    settings = make_settings(verifier_provider=None)

    assert harness.run(run_id, settings, verifier_client=None) == RunStatus.FAILED
    assert harness.get_run(run_id).failure_reason == (
        "config: no verifier provider given: set VERIFIER_PROVIDER"
    )
    assert harness.writers.total_calls == 0


def test_unexpected_exception_is_a_code_error(harness: Harness) -> None:
    harness.writers = Writers(gemini=[RuntimeError("boom")])
    run_id = create_run(harness.factory, ONE_GEMINI_PROMPT)

    assert harness.run(run_id) == RunStatus.FAILED
    assert harness.get_run(run_id).failure_reason == "code: RuntimeError: boom"
