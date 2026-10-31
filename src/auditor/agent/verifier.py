"""The verification agent loop: one answer in, validated claims (or a typed failure) out.

for each turn, up to max_turns:
    ask the model (with retries for transient errors)
    no tool call       -> nudge it and continue
    submit_claims      -> validate; success, or send the issues back and continue
    other tool calls   -> run them through the executor and continue
out of turns           -> fail as prompt (or tool, if only tool calls kept failing)
"""

import random
import time
from collections.abc import Callable

from pydantic import ValidationError

from auditor.agent.prompts import NUDGE, SYSTEM_PROMPTS, build_user_message
from auditor.agent.schemas import SubmitClaimsArgs, ValidatedClaim, VerificationResult
from auditor.agent.tools import (
    AGENT_TOOLS,
    SUBMIT_CLAIMS,
    SUBMIT_CLAIMS_TOOL,
    ToolExecutor,
    tool_result_message,
)
from auditor.agent.validator import validate_claims
from auditor.catalogue.repository import Catalogue
from auditor.enums import ErrorType
from auditor.llm.errors import (
    PermanentProviderError,
    ProviderConfigError,
    ProviderTimeoutError,
    TransientProviderError,
)
from auditor.llm.retry import call_with_retries
from auditor.llm.types import (
    UNPARSED_ARGUMENTS_KEY,
    LLMClient,
    Message,
    ModelResponse,
    TokenUsage,
    ToolCall,
)


def verify_answer(
    *,
    answer_text: str,
    client: LLMClient,
    catalogue: Catalogue,
    market: str | None = None,
    prompt_version: str = "v1",
    max_turns: int = 4,
    max_retries: int = 3,
    sleep: Callable[[float], None] = time.sleep,
    rand: Callable[[], float] = random.random,
    clock: Callable[[], float] = time.perf_counter,
) -> VerificationResult:
    """Verify one answer. Never raises, except ProviderConfigError.

    Why the exception: a missing key or rejected credentials will fail EVERY answer the
    same way, so the caller must stop the whole run instead of recording the same failure
    hundreds of times. Every other problem becomes a failed result, so one bad answer
    cannot crash a run.
    """
    system = SYSTEM_PROMPTS[prompt_version]
    messages: list[Message] = [
        Message(role="user", content=build_user_message(answer_text, market))
    ]
    executor = ToolExecutor(catalogue)
    known_brand_ids = {brand.brand_id for brand in catalogue.list_brands()}
    started = clock()
    turns = 0
    submit_attempts = 0
    tokens = TokenUsage()

    def finish(
        claims: list[ValidatedClaim] | None = None,
        error_type: ErrorType | None = None,
        detail: str | None = None,
        timed_out: bool = False,
    ) -> VerificationResult:
        return VerificationResult(
            ok=error_type is None,
            claims=tuple(claims or ()),
            model=client.model,
            prompt_version=prompt_version,
            turns=turns,
            tokens=tokens,
            latency_ms=(clock() - started) * 1000,
            error_type=error_type,
            error_detail=detail,
            timed_out=timed_out,
            exchanges=tuple(messages),
        )

    try:
        while turns < max_turns:
            turns += 1
            # On the last turn only submit_claims is offered, and the model must call it.
            # Without this, a model could spend its last turn browsing and never answer.
            last_turn = turns == max_turns
            response = _ask(
                client,
                system=system,
                messages=messages,
                last_turn=last_turn,
                max_retries=max_retries,
                sleep=sleep,
                rand=rand,
            )
            tokens = _add_tokens(tokens, response.tokens)
            messages.append(response.to_message())

            if not response.tool_calls:
                messages.append(Message(role="user", content=NUDGE))
                continue

            if any(call.name == SUBMIT_CLAIMS for call in response.tool_calls):
                submit_attempts += 1
                claims, issues = _check_submission(
                    response.tool_calls, answer_text, executor.seen_fact_ids, known_brand_ids
                )
                if not issues:
                    return finish(claims=claims)
                # Send the problems back so the model can fix them while turns remain.
                for call in response.tool_calls:
                    result = (
                        {"accepted": False, "problems": issues}
                        if call.name == SUBMIT_CLAIMS
                        else {"error": "not run: submit_claims must be the only tool call"}
                    )
                    messages.append(tool_result_message(call, result))
                continue

            for call in response.tool_calls:
                messages.append(tool_result_message(call, executor.execute(call)))

        # Out of turns. If the model never got as far as submitting and its tool calls
        # kept failing, the tools are the likely cause; otherwise its output was the problem.
        if submit_attempts == 0 and executor.error_count > 0:
            return finish(
                error_type=ErrorType.TOOL,
                detail=f"no valid submit_claims after {turns} turns; "
                f"{executor.error_count} tool call(s) failed",
            )
        return finish(
            error_type=ErrorType.PROMPT,
            detail=f"no valid submit_claims after {turns} turns "
            f"({submit_attempts} invalid submission(s))",
        )

    except ProviderConfigError:
        raise
    except TransientProviderError as exc:
        # Still failing after every retry.
        return finish(
            error_type=ErrorType.PROVIDER,
            detail=str(exc),
            timed_out=isinstance(exc, ProviderTimeoutError),
        )
    except PermanentProviderError as exc:
        return finish(error_type=ErrorType.PROVIDER, detail=str(exc))
    except Exception as exc:
        # A bug in our code. Caught so one answer cannot crash a whole run.
        return finish(error_type=ErrorType.CODE, detail=f"{type(exc).__name__}: {exc}")


def _ask(
    client: LLMClient,
    *,
    system: str,
    messages: list[Message],
    last_turn: bool,
    max_retries: int,
    sleep: Callable[[float], None],
    rand: Callable[[], float],
) -> ModelResponse:
    tools = (SUBMIT_CLAIMS_TOOL,) if last_turn else AGENT_TOOLS
    required_tool = SUBMIT_CLAIMS if last_turn else None
    # A snapshot of the conversation, so a retry sends exactly the same request.
    snapshot = tuple(messages)
    return call_with_retries(
        lambda: client.generate(
            system=system, messages=snapshot, tools=tools, required_tool=required_tool
        ),
        max_retries=max_retries,
        sleep=sleep,
        rand=rand,
    )


def _check_submission(
    calls: tuple[ToolCall, ...],
    answer_text: str,
    seen_fact_ids: set[str],
    known_brand_ids: set[str],
) -> tuple[list[ValidatedClaim], list[str]]:
    """Return (claims, issues) for a turn that called submit_claims."""
    issues = []
    if len(calls) > 1:
        # The final answer must not depend on tool results the model has not seen yet.
        issues.append("submit_claims must be the only tool call in its turn")

    submit = next(call for call in calls if call.name == SUBMIT_CLAIMS)
    if UNPARSED_ARGUMENTS_KEY in submit.arguments:
        return [], [*issues, "submit_claims arguments were not a valid JSON object"]
    try:
        args = SubmitClaimsArgs.model_validate(submit.arguments)
    except ValidationError as exc:
        details = [
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        ]
        return [], [*issues, *details]

    claims, claim_issues = validate_claims(
        answer_text, args.claims, seen_fact_ids=seen_fact_ids, known_brand_ids=known_brand_ids
    )
    issues.extend(claim_issues)
    return ([] if issues else claims), issues


def _add_tokens(total: TokenUsage, more: TokenUsage) -> TokenUsage:
    """Add token counts. A count stays None only if no response reported it."""

    def add(a: int | None, b: int | None) -> int | None:
        if a is None and b is None:
            return None
        return (a or 0) + (b or 0)

    return TokenUsage(
        input_tokens=add(total.input_tokens, more.input_tokens),
        output_tokens=add(total.output_tokens, more.output_tokens),
        thinking_tokens=add(total.thinking_tokens, more.thinking_tokens),
    )
