"""Verifier fallback: verify with the main verifier; if it fails with a provider error,
verify the same answer again, from the start, with the fallback verifier.

Why only `provider` errors: those mean the model API itself failed (retries used up,
timeout, a rejected request, an empty reply), so another provider may well succeed.
- `config` errors (missing key, rejected credentials) are still raised: a person must
  fix them, and they would fail every answer the same way.
- `prompt` / `tool` errors mean the model answered but badly; switching models there
  would hide a quality problem, so they are recorded as they are.

The answer is always verified from the start: a conversation cannot be handed from one
provider to another halfway (Gemini, for one, needs its own hidden turn data replayed).
"""

from collections.abc import Callable
from dataclasses import dataclass

from auditor.agent.schemas import VerificationResult
from auditor.agent.verifier import verify_answer
from auditor.enums import ErrorType, Provider
from auditor.llm.types import LLMClient


@dataclass(frozen=True)
class Verifier:
    """A verifier client and the provider it belongs to (stored on the answer)."""

    provider: Provider | None
    client: LLMClient


@dataclass(frozen=True)
class FailedAttempt:
    """The main verifier's failed result, kept when the fallback took over."""

    provider: Provider | None
    result: VerificationResult


@dataclass(frozen=True)
class VerifyOutcome:
    result: VerificationResult  # the result to save
    provider: Provider | None  # the provider that produced `result`
    fallback_from: FailedAttempt | None = None  # set only when the fallback was used


def should_fall_back(result: VerificationResult) -> bool:
    return not result.ok and result.error_type == ErrorType.PROVIDER


def verify_with_fallback(
    *,
    main: Verifier,
    fallback: Verifier | None,
    can_fall_back: Callable[[VerificationResult], bool] = lambda first: True,
    **verify_kwargs,
) -> VerifyOutcome:
    """Run verify_answer with `main`, and with `fallback` if the main one failed with a
    provider error. `can_fall_back(first_result)` lets the caller say no, for example
    when the run's budget has no room for another full verification.

    Like verify_answer, this raises only ProviderConfigError (from either verifier).
    """
    first = verify_answer(client=main.client, **verify_kwargs)
    if fallback is None or not should_fall_back(first) or not can_fall_back(first):
        return VerifyOutcome(result=first, provider=main.provider)
    second = verify_answer(client=fallback.client, **verify_kwargs)
    return VerifyOutcome(
        result=second,
        provider=fallback.provider,
        fallback_from=FailedAttempt(provider=main.provider, result=first),
    )
