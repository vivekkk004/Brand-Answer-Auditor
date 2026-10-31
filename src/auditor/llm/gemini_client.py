"""Google Gemini client (google-genai SDK 2.x)."""

import json
from collections.abc import Sequence
from typing import Any

import httpx
import httpx2
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from auditor.llm.errors import (
    PermanentProviderError,
    ProviderError,
    ProviderTimeoutError,
    TransientProviderError,
    error_for_status,
)
from auditor.llm.types import Message, ModelResponse, TokenUsage, ToolCall, ToolSpec

# Gemini may return a function call without an ID. We then make one up so the agent can
# match results to calls, and leave it out when sending the result back to Gemini.
GENERATED_ID_PREFIX = "gemini-call-"

# google-genai raises raw httpx/httpx2 exceptions for timeouts and network failures.
TIMEOUT_ERRORS = (httpx.TimeoutException, httpx2.TimeoutException)
NETWORK_ERRORS = (httpx.NetworkError, httpx2.NetworkError)


class GeminiClient:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float,
        temperature: float | None,
        sdk_client: Any = None,
    ) -> None:
        self.model = model
        self._temperature = temperature
        self._client = sdk_client or genai.Client(
            api_key=api_key, http_options=gemini_http_options(timeout_seconds)
        )

    def generate(
        self,
        *,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        required_tool: str | None = None,
    ) -> ModelResponse:
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=self._temperature,
            tools=[types.Tool(function_declarations=[to_gemini_function(t) for t in tools])]
            if tools
            else None,
            tool_config=_forced_tool_config(required_tool),
            # Without this the SDK may run Python functions itself. Our loop must see and
            # validate every tool call, so we always run tools ourselves.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        try:
            response = self._client.models.generate_content(
                model=self.model, contents=to_gemini_contents(messages), config=config
            )
        except (genai_errors.APIError, *TIMEOUT_ERRORS, *NETWORK_ERRORS) as exc:
            raise map_gemini_error(exc) from exc
        return from_gemini_response(response)


def gemini_http_options(timeout_seconds: float) -> types.HttpOptions:
    """The SDK takes the timeout in MILLISECONDS. attempts=1 turns off SDK retries, so
    call_with_retries is the only retry loop."""
    return types.HttpOptions(
        timeout=int(timeout_seconds * 1000),
        retry_options=types.HttpRetryOptions(attempts=1),
    )


def to_gemini_function(tool: ToolSpec) -> types.FunctionDeclaration:
    return types.FunctionDeclaration(
        name=tool.name, description=tool.description, parameters_json_schema=tool.parameters
    )


def to_gemini_contents(messages: Sequence[Message]) -> list[types.Content]:
    """Convert our messages to Gemini contents.

    Two Gemini rules shape this:
    - All results for one model turn's tool calls go back together in ONE user turn.
    - A previous model turn is replayed exactly as received (Message.raw), because it can
      carry hidden fields such as thought signatures that the model needs to continue.
    """
    contents: list[types.Content] = []
    pending_results: list[types.Part] = []

    for message in messages:
        if message.role == "tool":
            pending_results.append(_function_response_part(message))
            continue
        if pending_results:
            contents.append(types.Content(role="user", parts=pending_results))
            pending_results = []

        if message.role == "user":
            contents.append(types.Content(role="user", parts=[types.Part(text=message.content)]))
        elif message.raw is not None:
            contents.append(message.raw)
        else:
            contents.append(_model_content(message))

    if pending_results:
        contents.append(types.Content(role="user", parts=pending_results))
    return contents


def from_gemini_response(response: types.GenerateContentResponse) -> ModelResponse:
    candidate = response.candidates[0] if response.candidates else None
    if candidate is None or candidate.content is None or not candidate.content.parts:
        # Usually a safety block. Asking again gives the same result.
        block_reason = response.prompt_feedback.block_reason if response.prompt_feedback else None
        finish_reason = candidate.finish_reason if candidate else None
        raise PermanentProviderError(
            f"Gemini returned no content (block_reason={block_reason}, "
            f"finish_reason={finish_reason})"
        )

    content = candidate.content
    texts = []
    calls = []
    for part in content.parts or []:
        if part.function_call is not None:
            calls.append(
                ToolCall(
                    id=part.function_call.id or f"{GENERATED_ID_PREFIX}{len(calls)}",
                    name=part.function_call.name or "",
                    arguments=dict(part.function_call.args or {}),
                )
            )
        elif part.text and not part.thought:
            # Thought summaries are the model's working notes, not its answer.
            texts.append(part.text)

    return ModelResponse(
        text="".join(texts) or None,
        tool_calls=tuple(calls),
        tokens=_token_usage(response.usage_metadata),
        raw=content,
    )


def map_gemini_error(exc: Exception) -> ProviderError:
    if isinstance(exc, genai_errors.APIError):
        return error_for_status(exc.code, f"Gemini {exc.code} {exc.status}: {exc.message}")
    if isinstance(exc, TIMEOUT_ERRORS):
        return ProviderTimeoutError(f"Gemini request timed out: {exc}")
    if isinstance(exc, NETWORK_ERRORS):
        return TransientProviderError(f"Gemini connection error: {exc}")
    return PermanentProviderError(f"Gemini error: {exc}")


def _forced_tool_config(required_tool: str | None) -> types.ToolConfig | None:
    if required_tool is None:
        return None
    return types.ToolConfig(
        function_calling_config=types.FunctionCallingConfig(
            mode=types.FunctionCallingConfigMode.ANY, allowed_function_names=[required_tool]
        )
    )


def _function_response_part(message: Message) -> types.Part:
    result = json.loads(message.content)
    call_id = message.tool_call_id
    if call_id is not None and call_id.startswith(GENERATED_ID_PREFIX):
        call_id = None
    return types.Part(
        function_response=types.FunctionResponse(
            id=call_id,
            name=message.tool_name,
            # Gemini wants an object; wrap anything else.
            response=result if isinstance(result, dict) else {"output": result},
        )
    )


def _model_content(message: Message) -> types.Content:
    """Build a model turn by hand (only used when no raw turn was kept, e.g. in tests)."""
    parts = [types.Part(text=message.content)] if message.content else []
    for call in message.tool_calls:
        call_id = None if call.id.startswith(GENERATED_ID_PREFIX) else call.id
        parts.append(
            types.Part(
                function_call=types.FunctionCall(id=call_id, name=call.name, args=call.arguments)
            )
        )
    return types.Content(role="model", parts=parts)


def _token_usage(usage: types.GenerateContentResponseUsageMetadata | None) -> TokenUsage:
    if usage is None:
        return TokenUsage()
    output = None
    if usage.candidates_token_count is not None or usage.thoughts_token_count is not None:
        output = (usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0)
    return TokenUsage(
        input_tokens=usage.prompt_token_count,
        output_tokens=output,
        thinking_tokens=usage.thoughts_token_count,
    )
