"""OpenAI Chat Completions client (openai SDK 3.x).

Also used for OpenAI-compatible APIs (Groq): `base_url` points the SDK elsewhere and
`provider_label` names that provider in error messages. The defaults are plain OpenAI.
"""

import json
from collections.abc import Sequence
from typing import Any

import openai
from openai import OpenAI

from auditor.llm.errors import (
    PermanentProviderError,
    ProviderError,
    ProviderTimeoutError,
    TransientProviderError,
    error_for_status,
)
from auditor.llm.types import (
    UNPARSED_ARGUMENTS_KEY,
    Message,
    ModelResponse,
    TokenUsage,
    ToolCall,
    ToolSpec,
)


class OpenAIClient:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float,
        temperature: float | None,
        sdk_client: Any = None,
        base_url: str | None = None,
        provider_label: str = "OpenAI",
    ) -> None:
        self.model = model
        self._temperature = temperature
        self._label = provider_label
        # max_retries=0: the SDK would otherwise retry on its own, hidden from our
        # retry policy and our latency numbers. call_with_retries is the only retry loop.
        # base_url=None keeps the SDK's own default (the OpenAI API).
        self._client = sdk_client or OpenAI(
            api_key=api_key, base_url=base_url, timeout=timeout_seconds, max_retries=0
        )

    def generate(
        self,
        *,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        required_tool: str | None = None,
    ) -> ModelResponse:
        request: dict[str, Any] = {
            "model": self.model,
            "messages": to_openai_messages(system, messages),
        }
        if tools:
            request["tools"] = [to_openai_tool(tool) for tool in tools]
        if required_tool is not None:
            request["tool_choice"] = {"type": "function", "function": {"name": required_tool}}
        if self._temperature is not None:
            request["temperature"] = self._temperature

        try:
            completion = self._client.chat.completions.create(**request)
        except openai.OpenAIError as exc:
            raise map_openai_error(exc, self._label) from exc
        return from_openai_completion(completion, self._label)


def to_openai_tool(tool: ToolSpec) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        },
    }


def to_openai_messages(system: str, messages: Sequence[Message]) -> list[dict[str, Any]]:
    # An empty system prompt is left out: audit answers are generated with none (SPEC 6.4).
    converted: list[dict[str, Any]] = [{"role": "system", "content": system}] if system else []
    for message in messages:
        if message.role == "user":
            converted.append({"role": "user", "content": message.content})
        elif message.role == "assistant":
            turn: dict[str, Any] = {"role": "assistant", "content": message.content or None}
            if message.tool_calls:
                turn["tool_calls"] = [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {"name": call.name, "arguments": _arguments_text(call)},
                    }
                    for call in message.tool_calls
                ]
            converted.append(turn)
        else:
            converted.append(
                {"role": "tool", "tool_call_id": message.tool_call_id, "content": message.content}
            )
    return converted


def from_openai_completion(completion: Any, label: str = "OpenAI") -> ModelResponse:
    if not completion.choices:
        raise PermanentProviderError(f"{label} returned no choices")
    message = completion.choices[0].message

    calls = []
    for call in message.tool_calls or []:
        # We only offer function tools, so any other kind is a malformed reply.
        if call.type != "function":
            raise PermanentProviderError(f"unsupported tool call type {call.type!r}")
        calls.append(
            ToolCall(
                id=call.id,
                name=call.function.name,
                arguments=parse_arguments(call.function.arguments),
            )
        )

    usage = completion.usage
    tokens = TokenUsage(
        input_tokens=usage.prompt_tokens if usage else None,
        output_tokens=usage.completion_tokens if usage else None,
    )
    return ModelResponse(text=message.content, tool_calls=tuple(calls), tokens=tokens, raw=message)


def parse_arguments(raw: str) -> dict[str, Any]:
    """Tool arguments arrive as JSON text. Bad JSON must not crash the agent: it is
    kept as {"_unparsed": raw} so the agent can tell the model what went wrong."""
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {UNPARSED_ARGUMENTS_KEY: raw}
    if not isinstance(value, dict):
        return {UNPARSED_ARGUMENTS_KEY: raw}
    return value


def map_openai_error(exc: openai.OpenAIError, label: str = "OpenAI") -> ProviderError:
    # APITimeoutError is a subclass of APIConnectionError, so it must be checked first.
    if isinstance(exc, openai.APITimeoutError):
        return ProviderTimeoutError(f"{label} request timed out: {exc}")
    if isinstance(exc, openai.APIConnectionError):
        return TransientProviderError(f"{label} connection error: {exc}")
    if isinstance(exc, openai.APIStatusError):
        return error_for_status(exc.status_code, f"{label} {exc.status_code}: {exc.message}")
    return PermanentProviderError(f"{label} error: {exc}")


def _arguments_text(call: ToolCall) -> str:
    # Replay what the model actually sent, even when it was not valid JSON.
    if set(call.arguments) == {UNPARSED_ARGUMENTS_KEY}:
        return call.arguments[UNPARSED_ARGUMENTS_KEY]
    return json.dumps(call.arguments)
