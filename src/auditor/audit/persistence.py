"""Writing a verification result to the database."""

import uuid

from sqlalchemy.orm import Session

from auditor.agent.fallback import FailedAttempt
from auditor.agent.schemas import VerificationResult
from auditor.db import models as db
from auditor.enums import AnswerStatus, ClaimLabel, Provider
from auditor.llm.types import Message, TokenUsage


def save_verification(
    session: Session,
    answer: db.Answer,
    result: VerificationResult,
    verifier_provider: Provider | None,
    fallback_from: FailedAttempt | None = None,
) -> None:
    """Record the result on the answer; on success add its claims and review items.

    All or nothing (SPEC 4.9): everything is added to the same session, and the caller
    commits once. A failed result stores its error type and NO claims, so a half-checked
    answer can never look like a checked one.

    Every contradicted claim gets a review item, because a contradiction accuses a brand
    of a wrong fact, and a person should confirm it before anyone acts on it.

    `fallback_from` is the main verifier's failed attempt when the fallback verifier
    produced `result`. The verifier fields describe `result`; the failed attempt is kept
    under usage["fallback_from"], and its tokens are added to usage["verification"] so
    cost totals include every verification call that was paid for.
    """
    answer.verifier_provider = verifier_provider
    answer.verifier_model = result.model
    answer.prompt_version = result.prompt_version
    answer.verification_turns = result.turns
    answer.verification_latency_ms = result.latency_ms
    answer.timed_out = result.timed_out
    verification = usage_dict(result.tokens)
    extra: dict = {}
    if fallback_from is not None:
        failed = fallback_from.result
        verification = add_usage(verification, usage_dict(failed.tokens))
        extra["fallback_from"] = {
            "provider": fallback_from.provider.value if fallback_from.provider else None,
            "model": failed.model,
            "error_type": failed.error_type.value if failed.error_type else None,
            "error_detail": failed.error_detail,
            "timed_out": failed.timed_out,
            "turns": failed.turns,
            "latency_ms": failed.latency_ms,
            "tokens": usage_dict(failed.tokens),
        }
    # A new dict, so SQLAlchemy sees the JSON column change.
    answer.usage = {**answer.usage, "verification": verification, **extra}
    answer.exchanges = [message_dict(message) for message in result.exchanges]

    if not result.ok:
        answer.status = AnswerStatus.VERIFICATION_FAILED
        answer.error_type = result.error_type
        answer.error_message = result.error_detail
        return

    answer.status = AnswerStatus.VERIFIED
    for validated in result.claims:
        claim = db.Claim(
            # Set here so the review item can point at the claim before the flush.
            id=uuid.uuid4(),
            answer_id=answer.id,
            quote=validated.quote,
            start_offset=validated.start,
            end_offset=validated.end,
            brand_id=validated.brand_id,
            product=validated.product,
            attribute=validated.attribute,
            label=validated.label,
            fact_ids=list(validated.fact_ids),
            rationale=validated.rationale,
        )
        session.add(claim)
        if validated.label == ClaimLabel.CONTRADICTED:
            session.add(db.ReviewItem(client_id=answer.client_id, claim_id=claim.id))


def usage_dict(tokens: TokenUsage) -> dict[str, int | None]:
    return {
        "input": tokens.input_tokens,
        "output": tokens.output_tokens,
        "thinking": tokens.thinking_tokens,
    }


def add_usage(a: dict[str, int | None], b: dict[str, int | None]) -> dict[str, int | None]:
    """Add two token counts; a count stays None only if neither side reported it."""
    return {
        key: None if a[key] is None and b[key] is None else (a[key] or 0) + (b[key] or 0)
        for key in a
    }


def message_dict(message: Message) -> dict:
    """A conversation message as plain JSON. The provider's raw turn is left out: it is
    SDK-specific and only needed while the conversation is running."""
    return {
        "role": message.role,
        "content": message.content,
        "tool_calls": [
            {"id": call.id, "name": call.name, "arguments": call.arguments}
            for call in message.tool_calls
        ],
        "tool_call_id": message.tool_call_id,
        "tool_name": message.tool_name,
    }
