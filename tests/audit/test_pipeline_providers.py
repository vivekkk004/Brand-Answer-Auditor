"""Audit runs with Groq as a third answer provider, and the verifier fallback."""

import pytest
from sqlalchemy.orm import Session, sessionmaker

from auditor.enums import AnswerStatus, ErrorType, Provider, RunStatus
from auditor.llm.errors import PermanentProviderError
from auditor.llm.fake import ScriptedClient

from .fakes import GROQ_TEXT, FakeVerifier, create_run, make_settings
from .test_pipeline import ONE_GEMINI_PROMPT, Harness, inclusion


@pytest.fixture
def harness(seeded: sessionmaker[Session]) -> Harness:
    return Harness(seeded)


ALL_THREE = {
    "category": "earbuds",
    "prompt_ids": ["p01"],
    "answer_providers": ["gemini", "openai", "groq"],
    "repeats": 2,
}
FALLBACK_SETTINGS = {
    "verifier_fallback_provider": "openai",
    "verifier_fallback_model": "fallback-model",
}


def failing_verifier(times: int = 20) -> ScriptedClient:
    return ScriptedClient([PermanentProviderError("Gemini 400: bad request")] * times)


def test_a_run_can_ask_gemini_openai_and_groq(harness: Harness) -> None:
    run_id = create_run(harness.factory, ALL_THREE)

    assert harness.run(run_id) == RunStatus.COMPLETED
    answers = harness.answers(run_id)
    assert sorted((a.provider, a.model) for a in answers) == sorted(
        [(Provider.GEMINI, "gemini-answer")] * 2
        + [(Provider.OPENAI, "openai-answer")] * 2
        + [(Provider.GROQ, "groq-answer")] * 2
    )
    assert all(a.status == AnswerStatus.VERIFIED for a in answers)
    assert {a.text for a in answers if a.provider == Provider.GROQ} == {GROQ_TEXT}

    metrics = harness.get_run(run_id).metrics
    # Groq's answers name Kovalt, not Zentro; per-model inclusion keeps them apart.
    assert inclusion(metrics, "kovalt", "groq-answer")["k"] == 2
    assert inclusion(metrics, "zentro", "groq-answer")["k"] == 0


def test_groq_answer_failures_never_fall_back_to_another_assistant(harness: Harness) -> None:
    harness.writers.by_provider[Provider.GROQ].script = [PermanentProviderError("Groq 400")]
    run_id = create_run(harness.factory, ALL_THREE)

    harness.run(
        run_id, settings=make_settings(**FALLBACK_SETTINGS), fallback_verifier_client=FakeVerifier()
    )
    groq = [a for a in harness.answers(run_id) if a.provider == Provider.GROQ]
    assert sorted(a.status for a in groq) == [AnswerStatus.GENERATION_FAILED, AnswerStatus.VERIFIED]
    assert {a.model for a in groq} == {"groq-answer"}  # never another provider's model


def test_verifier_falls_back_and_records_both_attempts(harness: Harness) -> None:
    fallback = FakeVerifier()
    run_id = create_run(harness.factory, ONE_GEMINI_PROMPT)

    status = harness.run(
        run_id,
        settings=make_settings(**FALLBACK_SETTINGS),
        verifier_client=failing_verifier(),
        fallback_verifier_client=fallback,
    )

    assert status == RunStatus.COMPLETED
    answers = harness.answers(run_id)
    assert [a.status for a in answers] == [AnswerStatus.VERIFIED] * 2
    for answer in answers:
        assert (answer.verifier_provider, answer.verifier_model) == (
            Provider.OPENAI,
            "fake-verifier",
        )
        failed = answer.usage["fallback_from"]
        assert (failed["provider"], failed["error_type"]) == ("gemini", ErrorType.PROVIDER.value)
        assert failed["error_detail"].startswith("Gemini 400")
        # FakeVerifier reports 50 in / 10 out per turn over 2 turns; the failed call
        # reported nothing, so the totals are the fallback's alone.
        assert answer.usage["verification"] == {"input": 100, "output": 20, "thinking": None}

    # Budget: 2 collection calls, then per answer the failed main turn + 2 fallback turns.
    main_turns = answers[0].usage["fallback_from"]["turns"]
    assert harness.get_run(run_id).model_calls == 2 + 2 * (main_turns + 2)
    assert fallback.calls == 4


def test_no_fallback_when_the_budget_has_no_room(harness: Harness) -> None:
    fallback = FakeVerifier()
    run_id = create_run(harness.factory, dict(ONE_GEMINI_PROMPT, max_model_calls=6))

    # Collect 2. Answer 1: reserve 4 (6); main fails after 1 turn, so 3 would be free
    # but the fallback needs 4 (3 + 4 > 6): no fallback, the failure is saved.
    status = harness.run(
        run_id,
        settings=make_settings(**FALLBACK_SETTINGS),
        verifier_client=failing_verifier(),
        fallback_verifier_client=fallback,
    )

    assert status == RunStatus.PARTIAL
    statuses = sorted(a.status for a in harness.answers(run_id))
    assert statuses == [AnswerStatus.PENDING, AnswerStatus.VERIFICATION_FAILED]
    assert fallback.calls == 0
    assert harness.get_run(run_id).model_calls == 3
