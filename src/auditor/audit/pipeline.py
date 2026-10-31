"""Audit run processing: claim a queued run, collect answers, verify them, compute metrics.

Design rules, and why:
- Every answer is committed on its own, and existing rows are skipped, so a run that
  stops halfway (crash, deploy, budget) resumes exactly where it left off.
- No database transaction is open during a model call: calls take seconds, and holding
  a transaction (and its locks) that long would block other work.
- The catalogue is read once per run into memory, so every answer in a run is checked
  against the same snapshot of facts.
"""

import itertools
import logging
import random
import time
import uuid
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from pydantic import ValidationError
from sqlalchemy import Select, select, update
from sqlalchemy.orm import Session, sessionmaker

from auditor.agent.verifier import verify_answer
from auditor.audit.mentions import MentionDetector
from auditor.audit.persistence import save_verification, usage_dict
from auditor.audit.run_config import RunConfig
from auditor.catalogue.repository import InMemoryCatalogue, SqlCatalogue
from auditor.catalogue.schema import CatalogueData
from auditor.config import Settings
from auditor.db import models as db
from auditor.db.models import utc_now
from auditor.enums import AnswerStatus, ClaimLabel, ErrorType, Provider, RunStatus
from auditor.llm.errors import (
    PermanentProviderError,
    ProviderConfigError,
    ProviderTimeoutError,
    TransientProviderError,
)
from auditor.llm.factory import build_answer_client, build_verifier_client
from auditor.llm.retry import call_with_retries
from auditor.llm.types import LLMClient, Message
from auditor.metrics import estimate_cost_usd, wilson_interval

logger = logging.getLogger(__name__)

SessionFactory = sessionmaker[Session]


class RunDataError(Exception):
    """The run's input is unusable (for example a category with no prompts)."""


@dataclass(frozen=True)
class PromptRow:
    """Plain prompt values, usable after the session that loaded them is closed."""

    id: str
    text: str
    market: str | None


# --- Claiming runs ---


def queued_run_query() -> Select[tuple[db.AuditRun]]:
    """The oldest queued run, locked for this transaction.

    FOR UPDATE locks the row; SKIP LOCKED makes another worker skip a row that is
    already locked instead of waiting for it. So two workers asking at the same moment
    get two different runs, and neither blocks. (SQLite ignores this clause; it allows
    one writer at a time anyway.)
    """
    return (
        select(db.AuditRun)
        .where(db.AuditRun.status == RunStatus.QUEUED)
        .order_by(db.AuditRun.created_at, db.AuditRun.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    )


def claim_next_run(
    session_factory: SessionFactory, now: Callable[[], datetime] = utc_now
) -> uuid.UUID | None:
    """Mark the oldest queued run as running and return its ID, or None if none is queued."""
    with session_factory.begin() as session:
        run = session.scalars(queued_run_query()).first()
        if run is None:
            return None
        run.status = RunStatus.RUNNING
        run.started_at = run.started_at or now()
        run.heartbeat_at = now()
        return run.id


def requeue_stale_runs(
    session_factory: SessionFactory,
    stale_after: timedelta,
    now: Callable[[], datetime] = utc_now,
) -> int:
    """Put runs whose worker has gone silent back in the queue; return how many.

    A worker that dies mid-run leaves its run "running" forever. The heartbeat is
    updated after every answer, so an old heartbeat means nobody is working on it.
    Requeueing is safe because processing resumes and skips answers already saved.
    """
    cutoff = now() - stale_after
    with session_factory.begin() as session:
        result = session.execute(
            update(db.AuditRun)
            .where(db.AuditRun.status == RunStatus.RUNNING, db.AuditRun.heartbeat_at < cutoff)
            .values(status=RunStatus.QUEUED)
        )
        return result.rowcount


# --- Processing one run ---


def process_run(
    run_id: uuid.UUID,
    *,
    session_factory: SessionFactory,
    settings: Settings,
    answer_client_for: Callable[[Provider], LLMClient] | None = None,
    verifier_client: LLMClient | None = None,
    sleep: Callable[[float], None] = time.sleep,
    rand: Callable[[], float] = random.random,
    now: Callable[[], datetime] = utc_now,
    should_stop: Callable[[], bool] = lambda: False,
) -> RunStatus:
    """Process one claimed run to the end and return its final status.

    Failures end the run with a reason that starts with its type:
    - "config: ..." for a missing key or model. It is an expected setup problem, so it
      is logged as one line, without a traceback.
    - "data: ..." for unusable input such as an unknown category.
    - "code: ..." for anything unexpected, logged with its traceback.
    """
    try:
        return _process(
            run_id,
            session_factory=session_factory,
            settings=settings,
            answer_client_for=answer_client_for
            or (lambda provider: build_answer_client(provider, settings)),
            verifier_client=verifier_client,
            sleep=sleep,
            rand=rand,
            now=now,
            should_stop=should_stop,
        )
    except ProviderConfigError as exc:
        logger.error("run %s failed: config: %s", run_id, exc)
        return _fail(session_factory, run_id, f"config: {exc}", now)
    except RunDataError as exc:
        logger.error("run %s failed: data: %s", run_id, exc)
        return _fail(session_factory, run_id, f"data: {exc}", now)
    except Exception as exc:
        logger.exception("run %s failed with an unexpected error", run_id)
        return _fail(session_factory, run_id, f"code: {type(exc).__name__}: {exc}", now)


def _process(
    run_id: uuid.UUID,
    *,
    session_factory: SessionFactory,
    settings: Settings,
    answer_client_for: Callable[[Provider], LLMClient],
    verifier_client: LLMClient | None,
    sleep: Callable[[float], None],
    rand: Callable[[], float],
    now: Callable[[], datetime],
    should_stop: Callable[[], bool],
) -> RunStatus:
    with session_factory() as session:
        run = session.get(db.AuditRun, run_id)
        if run is None:
            raise RunDataError(f"run {run_id} does not exist")
        try:
            config = RunConfig.model_validate(run.config)
        except ValidationError as exc:
            raise RunDataError(f"invalid run config: {exc.error_count()} problem(s)") from exc
        prompts = select_prompts(session, config)
        catalogue = load_catalogue_snapshot(session)

    # Build every client before the first call, so a missing key or model fails the run
    # at once instead of after half the answers have been paid for.
    answer_clients = {provider: answer_client_for(provider) for provider in config.answer_providers}
    verifier = verifier_client or build_verifier_client(settings)
    detector = MentionDetector(catalogue.brands)
    max_turns = settings.agent_max_turns

    # Step 1: collect answers, one model call per (prompt, provider, repeat).
    slots = itertools.product(prompts, config.answer_providers, range(config.repeats))
    for prompt, provider, repeat_index in slots:
        if should_stop():
            return _release(session_factory, run_id)
        client = answer_clients[provider]
        with session_factory() as session:
            exists = _answer_exists(session, run_id, prompt.id, client.model, repeat_index)
            budget_ok = _budget_allows(session, run_id, calls=1)
        if exists:
            continue  # saved before a restart; never pay for it twice
        if not budget_ok:
            return _finish(session_factory, run_id, RunStatus.PARTIAL, settings, now)

        answer = _collect_answer(
            client, provider, prompt, repeat_index, detector, settings, sleep, rand
        )
        with session_factory.begin() as session:
            run = session.get(db.AuditRun, run_id)
            run.model_calls += 1
            run.heartbeat_at = now()
            answer.run_id = run_id
            answer.client_id = run.client_id
            session.add(answer)

    # Step 2: verify every answer that has text and no result yet.
    with session_factory() as session:
        pending_ids = session.scalars(
            select(db.Answer.id)
            .where(db.Answer.run_id == run_id, db.Answer.status == AnswerStatus.PENDING)
            .order_by(db.Answer.created_at, db.Answer.id)
        ).all()
    verifier_catalogue = InMemoryCatalogue(catalogue)

    for answer_id in pending_ids:
        if should_stop():
            return _release(session_factory, run_id)
        # Reserve the worst case (every turn) before starting, so verification can never
        # push the run over its budget. Unused turns are refunded afterwards.
        with session_factory.begin() as session:
            budget_ok = _budget_allows(session, run_id, calls=max_turns)
            if budget_ok:
                session.get(db.AuditRun, run_id).model_calls += max_turns
                answer = session.get(db.Answer, answer_id)
                answer_text, market = answer.text, answer.market
        if not budget_ok:
            return _finish(session_factory, run_id, RunStatus.PARTIAL, settings, now)

        result = verify_answer(
            answer_text=answer_text,
            client=verifier,
            catalogue=verifier_catalogue,
            market=market,
            prompt_version=config.agent_version,
            max_turns=max_turns,
            max_retries=settings.llm_max_retries,
            sleep=sleep,
            rand=rand,
        )

        with session_factory.begin() as session:
            run = session.get(db.AuditRun, run_id)
            run.model_calls -= max_turns - result.turns
            run.heartbeat_at = now()
            save_verification(
                session, session.get(db.Answer, answer_id), result, settings.verifier_provider
            )

    return _finish(session_factory, run_id, RunStatus.COMPLETED, settings, now)


def select_prompts(session: Session, config: RunConfig) -> list[PromptRow]:
    prompts = session.scalars(
        select(db.Prompt).where(db.Prompt.category == config.category).order_by(db.Prompt.id)
    ).all()
    if not prompts:
        raise RunDataError(f"no prompts in category {config.category!r}")
    if config.prompt_ids is not None:
        by_id = {prompt.id: prompt for prompt in prompts}
        missing = [prompt_id for prompt_id in config.prompt_ids if prompt_id not in by_id]
        if missing:
            raise RunDataError(f"prompt IDs not in category {config.category!r}: {missing}")
        prompts = [by_id[prompt_id] for prompt_id in config.prompt_ids]
    return [PromptRow(id=p.id, text=p.text, market=p.market) for p in prompts]


def load_catalogue_snapshot(session: Session) -> CatalogueData:
    sql = SqlCatalogue(session)
    brands = sql.list_brands()
    facts = [fact for brand in brands for fact in sql.get_brand_facts(brand.brand_id)]
    return CatalogueData(brands=tuple(brands), facts=tuple(facts))


def _answer_exists(
    session: Session, run_id: uuid.UUID, prompt_id: str, model: str, repeat_index: int
) -> bool:
    return (
        session.scalars(
            select(db.Answer.id).where(
                db.Answer.run_id == run_id,
                db.Answer.prompt_id == prompt_id,
                db.Answer.model == model,
                db.Answer.repeat_index == repeat_index,
            )
        ).first()
        is not None
    )


def _budget_allows(session: Session, run_id: uuid.UUID, calls: int) -> bool:
    run = session.get(db.AuditRun, run_id)
    return run.model_calls + calls <= run.max_model_calls


def _collect_answer(
    client: LLMClient,
    provider: Provider,
    prompt: PromptRow,
    repeat_index: int,
    detector: MentionDetector,
    settings: Settings,
    sleep: Callable[[float], None],
    rand: Callable[[], float],
) -> db.Answer:
    """Ask the answer model the prompt (no system prompt) and build the answer row.

    A provider failure is recorded on the row (status generation_failed), not raised:
    one failed answer must not stop the run. Config errors are raised, because every
    other answer would fail the same way.
    """
    answer = db.Answer(
        prompt_id=prompt.id,
        provider=provider,
        model=client.model,
        repeat_index=repeat_index,
        market=prompt.market,
        brands_mentioned=[],
        usage={},
    )
    try:
        response = call_with_retries(
            lambda: client.generate(
                system="", messages=[Message(role="user", content=prompt.text)], tools=[]
            ),
            max_retries=settings.llm_max_retries,
            sleep=sleep,
            rand=rand,
        )
    except (TransientProviderError, PermanentProviderError) as exc:
        answer.status = AnswerStatus.GENERATION_FAILED
        answer.error_type = ErrorType.PROVIDER
        answer.error_message = str(exc)
        answer.timed_out = isinstance(exc, ProviderTimeoutError)
        return answer

    answer.usage = {"generation": usage_dict(response.tokens)}
    if not response.text or not response.text.strip():
        answer.status = AnswerStatus.GENERATION_FAILED
        answer.error_type = ErrorType.PROVIDER
        answer.error_message = "the model returned an empty answer"
        return answer
    answer.text = response.text
    answer.status = AnswerStatus.PENDING
    answer.brands_mentioned = detector.detect(response.text)
    return answer


def _release(session_factory: SessionFactory, run_id: uuid.UUID) -> RunStatus:
    """Graceful shutdown: hand the run back to the queue so another worker resumes it."""
    with session_factory.begin() as session:
        session.get(db.AuditRun, run_id).status = RunStatus.QUEUED
    return RunStatus.QUEUED


def _finish(
    session_factory: SessionFactory,
    run_id: uuid.UUID,
    status: RunStatus,
    settings: Settings,
    now: Callable[[], datetime],
) -> RunStatus:
    with session_factory.begin() as session:
        run = session.get(db.AuditRun, run_id)
        run.metrics = compute_run_metrics(session, run_id, settings)
        run.status = status
        run.finished_at = now()
    return status


def _fail(
    session_factory: SessionFactory,
    run_id: uuid.UUID,
    reason: str,
    now: Callable[[], datetime],
) -> RunStatus:
    with session_factory.begin() as session:
        run = session.get(db.AuditRun, run_id)
        if run is not None:
            run.status = RunStatus.FAILED
            run.failure_reason = reason
            run.finished_at = now()
    return RunStatus.FAILED


# --- Metrics ---


def compute_run_metrics(session: Session, run_id: uuid.UUID, settings: Settings) -> dict[str, Any]:
    """Every number in a run report, computed from the stored rows (SPEC 7)."""
    run = session.get(db.AuditRun, run_id)
    answers = session.scalars(select(db.Answer).where(db.Answer.run_id == run_id)).all()
    brand_ids = session.scalars(select(db.Brand.id).order_by(db.Brand.id)).all()
    claims = session.scalars(
        select(db.Claim).join(db.Answer).where(db.Answer.run_id == run_id)
    ).all()

    # Inclusion counts every answer that has text, whether or not it was verified yet.
    with_text = [answer for answer in answers if answer.text is not None]
    models = sorted({(answer.provider, answer.model) for answer in answers})
    inclusion = []
    for brand_id in brand_ids:
        for provider, model in models:
            group = [a for a in with_text if (a.provider, a.model) == (provider, model)]
            inclusion.append(_inclusion_row(brand_id, provider, model, group))
        inclusion.append(_inclusion_row(brand_id, None, None, with_text))

    label_counts = Counter(claim.label for claim in claims)
    total_claims = len(claims)
    labels = {
        label.value: {
            "count": label_counts[label],
            "share": label_counts[label] / total_claims if total_claims else None,
        }
        for label in ClaimLabel
    }

    tokens = {
        phase: _sum_usage(answer.usage.get(phase, {}) for answer in answers)
        for phase in ("generation", "verification")
    }
    tokens["total"] = _sum_usage(tokens.values())
    cost = estimate_cost_usd(
        tokens["total"]["input"],
        tokens["total"]["output"],
        settings.input_token_price_per_million,
        settings.output_token_price_per_million,
    )

    return {
        "answers": {
            "total": len(answers),
            **{status.value: sum(a.status == status for a in answers) for status in AnswerStatus},
        },
        "inclusion": inclusion,
        "claims": {"total": total_claims, "labels": labels},
        "errors_by_type": dict(
            sorted(Counter(a.error_type.value for a in answers if a.error_type).items())
        ),
        "tokens": tokens,
        "cost_usd": float(cost) if cost is not None else None,
        "model_calls": {"used": run.model_calls, "max": run.max_model_calls},
    }


def _inclusion_row(
    brand_id: str, provider: Provider | None, model: str | None, answers: list[db.Answer]
) -> dict[str, Any]:
    k = sum(brand_id in answer.brands_mentioned for answer in answers)
    n = len(answers)
    interval = wilson_interval(k, n)
    return {
        "brand_id": brand_id,
        "provider": provider.value if provider else None,
        "model": model,
        "k": k,
        "n": n,
        "rate": k / n if n else None,
        "ci_low": interval[0] if interval else None,
        "ci_high": interval[1] if interval else None,
    }


def _sum_usage(usages) -> dict[str, int | None]:
    """Add token counts; a total stays None only if no answer reported that count."""
    totals: dict[str, int | None] = {"input": None, "output": None, "thinking": None}
    for usage in usages:
        for key in totals:
            value = usage.get(key)
            if value is not None:
                totals[key] = (totals[key] or 0) + value
    return totals
