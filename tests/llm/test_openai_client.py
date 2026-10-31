import json
from typing import Any

import httpx
import openai
import pytest
from openai.types.chat import ChatCompletion

from auditor.llm.errors import (
    PermanentProviderError,
    ProviderConfigError,
    ProviderTimeoutError,
    TransientProviderError,
)
from auditor.llm.openai_client import (
    OpenAIClient,
    from_openai_completion,
    map_openai_error,
    to_openai_messages,
)
from auditor.llm.types import Message, ToolCall, ToolSpec

TOOL = ToolSpec("get_brand_facts", "Facts for one brand.", {"type": "object", "properties": {}})


def completion(message: dict[str, Any], usage: dict[str, int] | None = None) -> ChatCompletion:
    return ChatCompletion.model_validate(
        {
            "id": "cmpl-1",
            "object": "chat.completion",
            "created": 0,
            "model": "test-model",
            "choices": [{"index": 0, "finish_reason": "stop", "message": message}],
            "usage": usage,
        }
    )


class RecordingSdk:
    """Stands in for openai.OpenAI: records the request, returns a fixed completion."""

    def __init__(self, result: Any) -> None:
        self.requests: list[dict[str, Any]] = []
        self.result = result
        self.chat = self
        self.completions = self

    def create(self, **request: Any) -> Any:
        self.requests.append(request)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_messages_are_converted_to_openai_format() -> None:
    messages = [
        Message(role="user", content="Check this answer."),
        Message(
            role="assistant",
            tool_calls=(ToolCall("c1", "get_brand_facts", {"brand_id": "zentro"}),),
        ),
        Message(role="tool", content='{"facts": []}', tool_call_id="c1", tool_name="x"),
    ]

    assert to_openai_messages("Be careful.", messages) == [
        {"role": "system", "content": "Be careful."},
        {"role": "user", "content": "Check this answer."},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "c1",
                    "type": "function",
                    "function": {"name": "get_brand_facts", "arguments": '{"brand_id": "zentro"}'},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "c1", "content": '{"facts": []}'},
    ]


def test_empty_system_prompt_is_left_out() -> None:
    assert to_openai_messages("", [Message(role="user", content="Hi")]) == [
        {"role": "user", "content": "Hi"}
    ]


def test_unparsed_arguments_are_replayed_as_sent() -> None:
    call = ToolCall("c1", "get_brand_facts", {"_unparsed": "{brand_id: zentro"})
    converted = to_openai_messages("s", [Message(role="assistant", tool_calls=(call,))])
    assert converted[1]["tool_calls"][0]["function"]["arguments"] == "{brand_id: zentro"


def test_response_is_converted_and_bad_argument_json_does_not_crash() -> None:
    result = from_openai_completion(
        completion(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {"name": "get_brand_facts", "arguments": '{"brand_id": "x"}'},
                    },
                    {
                        "id": "c2",
                        "type": "function",
                        "function": {"name": "get_brand_facts", "arguments": "{not json"},
                    },
                    {
                        "id": "c3",
                        "type": "function",
                        "function": {"name": "get_brand_facts", "arguments": "[1, 2]"},
                    },
                ],
            },
            usage={"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150},
        )
    )

    assert result.text is None
    assert [call.arguments for call in result.tool_calls] == [
        {"brand_id": "x"},
        {"_unparsed": "{not json"},
        {"_unparsed": "[1, 2]"},
    ]
    assert (result.tokens.input_tokens, result.tokens.output_tokens) == (120, 30)


def test_missing_usage_gives_none_not_zero() -> None:
    result = from_openai_completion(completion({"role": "assistant", "content": "Hi"}))
    assert result.text == "Hi"
    assert result.tokens.input_tokens is None
    assert result.tokens.output_tokens is None


def test_generate_sends_tools_forced_choice_and_temperature() -> None:
    sdk = RecordingSdk(completion({"role": "assistant", "content": "done"}))
    client = OpenAIClient(
        api_key="test-key", model="m", timeout_seconds=5, temperature=0.0, sdk_client=sdk
    )

    client.generate(system="s", messages=[], tools=[TOOL], required_tool="get_brand_facts")

    request = sdk.requests[0]
    assert request["model"] == "m"
    assert request["temperature"] == 0.0
    assert request["tools"][0]["function"]["name"] == "get_brand_facts"
    assert request["tool_choice"] == {"type": "function", "function": {"name": "get_brand_facts"}}


def test_temperature_none_is_not_sent() -> None:
    sdk = RecordingSdk(completion({"role": "assistant", "content": "done"}))
    client = OpenAIClient(
        api_key="test-key", model="m", timeout_seconds=5, temperature=None, sdk_client=sdk
    )
    client.generate(system="s", messages=[], tools=[])
    assert "temperature" not in sdk.requests[0]
    assert "tools" not in sdk.requests[0]
    assert "tool_choice" not in sdk.requests[0]


REQUEST = httpx.Request("POST", "https://api.example.test/v1/chat/completions")


def status_error(cls: type[openai.APIStatusError], status: int) -> openai.APIStatusError:
    return cls("boom", response=httpx.Response(status, request=REQUEST), body=None)


@pytest.mark.parametrize(
    ("sdk_error", "expected"),
    [
        (openai.APITimeoutError(request=REQUEST), ProviderTimeoutError),
        (openai.APIConnectionError(request=REQUEST), TransientProviderError),
        (status_error(openai.RateLimitError, 429), TransientProviderError),
        (status_error(openai.InternalServerError, 503), TransientProviderError),
        (status_error(openai.AuthenticationError, 401), ProviderConfigError),
        (status_error(openai.PermissionDeniedError, 403), ProviderConfigError),
        (status_error(openai.BadRequestError, 400), PermanentProviderError),
        (status_error(openai.NotFoundError, 404), PermanentProviderError),
    ],
)
def test_sdk_errors_are_mapped(sdk_error: openai.OpenAIError, expected: type) -> None:
    assert type(map_openai_error(sdk_error)) is expected


def test_generate_raises_our_error_not_the_sdk_error() -> None:
    sdk = RecordingSdk(status_error(openai.RateLimitError, 429))
    client = OpenAIClient(
        api_key="test-key", model="m", timeout_seconds=5, temperature=None, sdk_client=sdk
    )
    with pytest.raises(TransientProviderError):
        client.generate(system="s", messages=[], tools=[])


def test_tool_arguments_are_json_objects() -> None:
    converted = to_openai_messages(
        "s", [Message(role="assistant", tool_calls=(ToolCall("c", "t", {"a": [1]}),))]
    )
    assert json.loads(converted[1]["tool_calls"][0]["function"]["arguments"]) == {"a": [1]}
