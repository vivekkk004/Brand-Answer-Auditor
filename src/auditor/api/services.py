"""The API's business logic. Route handlers only parse requests and call these functions.

Every lookup filters by the caller's client ID, and a row that belongs to someone else
is reported as 404, never 403: a 403 would confirm that the ID exists.
"""

import hashlib
import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auditor.agent.fallback import Verifier, verify_with_fallback
from auditor.agent.schemas import VerificationResult
from auditor.api.errors import ApiError
from auditor.api.schemas import (
    AnswerOut,
    ClaimOut,
    ReviewDecision,
    ReviewItemList,
    ReviewItemOut,
    RunList,
    RunOut,
    VerifyRequest,
)
from auditor.audit.mentions import MentionDetector
from auditor.audit.persistence import save_verification
from auditor.audit.pipeline import RunDataError, load_catalogue_snapshot, select_prompts
from auditor.audit.run_config import RunConfig
from auditor.catalogue.repository import InMemoryCatalogue
from auditor.config import Settings
from auditor.db import models as db
from auditor.db.models import utc_now
from auditor.enums import AnswerStatus, ErrorType, ReviewStatus, RunStatus
from auditor.llm.errors import ProviderConfigError
from auditor.llm.types import LLMClient

# --- POST /v1/verify ---


def verify_text(
    session: Session,
    client_id: uuid.UUID,
    request: VerifyRequest,
    settings: Settings,
    client_factory: Callable[[], LLMClient],
    fallback_client_factory: Callable[[], LLMClient | None] = lambda: None,
) -> AnswerOut:
    """Verify one answer now. The answer row is saved BEFORE the model is called, so a
    failed attempt is kept (and counted) too; its ID is returned in the error body."""
    catalogue = load_catalogue_snapshot(session)
    answer = db.Answer(
        client_id=client_id,
        text=request.text,
        market=request.market,
        status=AnswerStatus.PENDING,
        brands_mentioned=MentionDetector(catalogue.brands).detect(request.text),
        usage={},
    )
    session.add(answer)
    session.commit()

    try:
        main = Verifier(settings.verifier_provider, client_factory())
        fallback_client = fallback_client_factory()
        fallback = (
            Verifier(settings.verifier_fallback_provider, fallback_client)
            if fallback_client
            else None
        )
        outcome = verify_with_fallback(
            main=main,
            fallback=fallback,
            answer_text=request.text,
            catalogue=InMemoryCatalogue(catalogue),
            market=request.market,
            prompt_version=request.prompt_version,
            max_turns=settings.agent_max_turns,
            max_retries=settings.llm_max_retries,
        )
    except ProviderConfigError as exc:
        answer.status = AnswerStatus.VERIFICATION_FAILED
        answer.error_type = ErrorType.CONFIG
        answer.error_message = str(exc)
        session.commit()
        raise ApiError(503, "verifier_not_configured", str(exc), answer_id=str(answer.id)) from exc

    result = outcome.result
    save_verification(session, answer, result, outcome.provider, outcome.fallback_from)
    session.commit()
    if not result.ok:
        raise _verification_error(answer.id, result)
    return answer_out(session, answer)


def _verification_error(answer_id: uuid.UUID, result: VerificationResult) -> ApiError:
    """Map a failed verification to an HTTP status.

    502 and 504 say "the upstream model failed", not "you sent a bad request". A bug on
    our side (code, data) is a 500 with a generic message: internal details stay in the
    stored answer, not in the response.
    """
    error_type = result.error_type
    if error_type == ErrorType.PROVIDER and result.timed_out:
        status, code, message = 504, "provider_timeout", "the model provider timed out"
    elif error_type == ErrorType.PROVIDER:
        status, code, message = 502, "provider_error", result.error_detail or "provider error"
    elif error_type in (ErrorType.PROMPT, ErrorType.TOOL):
        status, code = 502, "invalid_model_output"
        message = result.error_detail or "the model did not produce a valid answer"
    else:
        status, code, message = 500, "internal_error", "verification failed unexpectedly"
    return ApiError(status, code, message, answer_id=str(answer_id), error_type=error_type.value)


# --- POST /v1/audit-runs ---


def request_hash(config: RunConfig) -> str:
    """SHA-256 of the canonical request: the validated config with defaults filled in,
    keys sorted, no spaces. Two bodies that mean the same thing get the same hash."""
    canonical = json.dumps(config.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def create_run(
    session: Session, client_id: uuid.UUID, config: RunConfig, idempotency_key: str
) -> tuple[db.AuditRun, bool]:
    """Queue a run, or replay the one already made with this key. Returns (run, replayed).

    Same key + same body: the existing run (a retried request must not start a second,
    paid run). Same key + different body: 409. Keys are per client.
    """
    body_hash = request_hash(config)
    existing = find_run_by_key(session, client_id, idempotency_key)
    if existing is not None:
        return _replay(existing, body_hash), True

    try:
        select_prompts(session, config)
    except RunDataError as exc:
        raise ApiError(422, "no_matching_prompts", str(exc)) from exc

    run = db.AuditRun(
        client_id=client_id,
        idempotency_key=idempotency_key,
        request_hash=body_hash,
        config=config.model_dump(mode="json"),
        max_model_calls=config.max_model_calls,
    )
    session.add(run)
    try:
        session.commit()
    except IntegrityError:
        # A concurrent request with the same key was inserted between our lookup and our
        # insert. The unique constraint stopped the duplicate; return the winner's run.
        session.rollback()
        winner = find_run_by_key(session, client_id, idempotency_key)
        if winner is None:
            raise
        return _replay(winner, body_hash), True
    return run, False


def find_run_by_key(
    session: Session, client_id: uuid.UUID, idempotency_key: str
) -> db.AuditRun | None:
    return session.scalars(
        select(db.AuditRun).where(
            db.AuditRun.client_id == client_id, db.AuditRun.idempotency_key == idempotency_key
        )
    ).first()


def _replay(existing: db.AuditRun, body_hash: str) -> db.AuditRun:
    if existing.request_hash != body_hash:
        raise ApiError(
            409,
            "idempotency_conflict",
            "this Idempotency-Key was already used with a different request body",
        )
    return existing


def get_run(session: Session, client_id: uuid.UUID, run_id: uuid.UUID) -> RunOut:
    run = session.get(db.AuditRun, run_id)
    if run is None or run.client_id != client_id:
        raise ApiError(404, "not_found", "audit run not found")
    return run_out(run)


def list_runs(
    session: Session,
    client_id: uuid.UUID,
    status: RunStatus | None,
    limit: int,
    offset: int,
) -> RunList:
    """The caller's runs, newest first, so a dashboard shows the latest work at the top."""
    query = (
        select(db.AuditRun)
        .where(db.AuditRun.client_id == client_id)
        .order_by(db.AuditRun.created_at.desc(), db.AuditRun.id)
        .limit(limit)
        .offset(offset)
    )
    if status is not None:
        query = query.where(db.AuditRun.status == status)
    items = [run_out(run) for run in session.scalars(query)]
    return RunList(items=items, limit=limit, offset=offset)


def run_out(run: db.AuditRun) -> RunOut:
    return RunOut(
        id=run.id,
        status=run.status,
        config=run.config,
        model_calls=run.model_calls,
        max_model_calls=run.max_model_calls,
        metrics=run.metrics,
        failure_reason=run.failure_reason,
        created_at=as_utc(run.created_at),
        started_at=as_utc(run.started_at),
        finished_at=as_utc(run.finished_at),
    )


# --- GET /v1/answers/{id} ---


def get_answer(session: Session, client_id: uuid.UUID, answer_id: uuid.UUID) -> AnswerOut:
    answer = session.get(db.Answer, answer_id)
    if answer is None or answer.client_id != client_id:
        raise ApiError(404, "not_found", "answer not found")
    return answer_out(session, answer)


def answer_out(session: Session, answer: db.Answer) -> AnswerOut:
    claims = session.scalars(
        select(db.Claim).where(db.Claim.answer_id == answer.id).order_by(db.Claim.start_offset)
    ).all()
    return AnswerOut(
        id=answer.id,
        run_id=answer.run_id,
        prompt_id=answer.prompt_id,
        provider=answer.provider,
        model=answer.model,
        repeat_index=answer.repeat_index,
        market=answer.market,
        text=answer.text,
        status=answer.status,
        error_type=answer.error_type,
        error_message=answer.error_message,
        brands_mentioned=answer.brands_mentioned,
        verifier_model=answer.verifier_model,
        prompt_version=answer.prompt_version,
        verification_turns=answer.verification_turns,
        verification_latency_ms=answer.verification_latency_ms,
        timed_out=answer.timed_out,
        usage=answer.usage,
        claims=[claim_out(claim) for claim in claims],
        exchanges=answer.exchanges,
        created_at=as_utc(answer.created_at),
    )


def claim_out(claim: db.Claim) -> ClaimOut:
    return ClaimOut(
        id=claim.id,
        quote=claim.quote,
        start=claim.start_offset,
        end=claim.end_offset,
        brand_id=claim.brand_id,
        product=claim.product,
        attribute=claim.attribute,
        label=claim.label,
        fact_ids=claim.fact_ids,
        rationale=claim.rationale,
    )


# --- Review queue ---


def list_review_items(
    session: Session,
    client_id: uuid.UUID,
    status: ReviewStatus | None,
    limit: int,
    offset: int,
) -> ReviewItemList:
    query = (
        select(db.ReviewItem, db.Claim)
        .join(db.Claim, db.ReviewItem.claim_id == db.Claim.id)
        .where(db.ReviewItem.client_id == client_id)
        .order_by(db.ReviewItem.created_at, db.ReviewItem.id)
        .limit(limit)
        .offset(offset)
    )
    if status is not None:
        query = query.where(db.ReviewItem.status == status)
    items = [review_item_out(item, claim) for item, claim in session.execute(query)]
    return ReviewItemList(items=items, limit=limit, offset=offset)


def decide_review_item(
    session: Session, client_id: uuid.UUID, item_id: uuid.UUID, decision: ReviewDecision
) -> ReviewItemOut:
    """Record a reviewer's decision. Each item is decided once: changing a decision later
    would silently rewrite the audit trail, so a second decision is a 409."""
    item = session.get(db.ReviewItem, item_id)
    if item is None or item.client_id != client_id:
        raise ApiError(404, "not_found", "review item not found")
    if item.status != ReviewStatus.OPEN:
        raise ApiError(409, "already_decided", f"this item was already {item.status}")
    item.status = ReviewStatus(decision.decision)
    item.note = decision.note
    item.resolved_at = utc_now()
    session.commit()
    return review_item_out(item, session.get(db.Claim, item.claim_id))


def review_item_out(item: db.ReviewItem, claim: db.Claim) -> ReviewItemOut:
    return ReviewItemOut(
        id=item.id,
        status=item.status,
        note=item.note,
        created_at=as_utc(item.created_at),
        resolved_at=as_utc(item.resolved_at),
        answer_id=claim.answer_id,
        claim=claim_out(claim),
    )


def as_utc(value: datetime | None) -> datetime | None:
    """Every timestamp we store is UTC, but SQLite drops the timezone when it stores one.
    Marking them all as UTC keeps responses identical on SQLite and PostgreSQL."""
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
