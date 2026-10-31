from typing import Any

import httpx
import httpx2
import pytest
from google.genai import errors as genai_errors
from google.genai import types

from auditor.llm.errors import (
    PermanentProviderError,
    ProviderConfigError,
    ProviderTimeoutError,
    TransientProviderError,
)
from auditor.llm.gemini_client import (
    GeminiClient,
    from_gemini_response,
    gemini_http_options,
    map_gemini_error,
    to_gemini_contents,
)
from auditor.llm.types import Message, ToolCall, ToolSpec

TOOL = ToolSpec("submit_claims", "Submit.", {"type": "object", "properties": {}})


def gemini_response(parts: list[dict[str, Any]], usage: dict[str, int] | None = None):
    return types.GenerateContentResponse.model_validate(
        {
            "candidates": [{"content": {"role": "model", "parts": parts}, "finish_reason": "STOP"}],
            "usage_metadata": usage,
        }
    )


class RecordingSdk:
    """Stands in for genai.Client: records the request, returns a fixed response."""

    def __init__(self, result: Any) -> None:
        self.requests: list[dict[str, Any]] = []
        self.result = result
        self.models = self

    def generate_content(self, **request: Any) -> Any:
        self.requests.append(request)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_parallel_tool_results_are_grouped_in_one_user_turn() -> None:
    model_turn = types.Content(
        role="model",
        parts=[
            types.Part(function_call=types.FunctionCall(id="a", name="get_brand_facts")),
            types.Part(function_call=types.FunctionCall(id="b", name="get_brand_facts")),
        ],
    )
    messages = [
        Message(role="user", content="Check this."),
        Message(role="assistant", raw=model_turn),
        Message(
            role="tool", content='{"facts": [1]}', tool_call_id="a", tool_name="get_brand_facts"
        ),
        Message(
            role="tool", content='{"facts": [2]}', tool_call_id="b", tool_name="get_brand_facts"
        ),
        Message(role="user", content="Now submit."),
    ]

    contents = to_gemini_contents(messages)

    assert [content.role for content in contents] == ["user", "model", "user", "user"]
    results = contents[2].parts
    assert [part.function_response.id for part in results] == ["a", "b"]
    assert [part.function_response.response for part in results] == [{"facts": [1]}, {"facts": [2]}]


def test_previous_model_turn_is_replayed_unchanged() -> None:
    # The thought signature is invisible to us but must go back to Gemini as it came.
    response = gemini_response(
        [
            {
                "function_call": {"name": "list_known_brands", "args": {}},
                "thought_signature": b"secret-signature",
            }
        ]
    )
    reply = from_gemini_response(response)

    contents = to_gemini_contents([Message(role="user", content="Go."), reply.to_message()])

    assert contents[1] is response.candidates[0].content
    assert contents[1].parts[0].thought_signature == b"secret-signature"


def test_generated_ids_are_not_sent_back_to_gemini() -> None:
    reply = from_gemini_response(
        gemini_response([{"function_call": {"name": "list_known_brands", "args": {}}}])
    )
    call = reply.tool_calls[0]
    assert call.id == "gemini-call-0"

    result = Message(role="tool", content="{}", tool_call_id=call.id, tool_name=call.name)
    contents = to_gemini_contents([reply.to_message(), result])

    assert contents[1].parts[0].function_response.id is None
    assert contents[1].parts[0].function_response.name == "list_known_brands"


def test_assistant_turn_without_raw_is_built_from_tool_calls() -> None:
    message = Message(
        role="assistant", content="Looking up.", tool_calls=(ToolCall("x1", "t", {"k": "v"}),)
    )
    content = to_gemini_contents([message])[0]
    assert content.role == "model"
    assert content.parts[0].text == "Looking up."
    assert content.parts[1].function_call.args == {"k": "v"}


def test_non_object_tool_result_is_wrapped() -> None:
    contents = to_gemini_contents(
        [Message(role="tool", content="[1, 2]", tool_call_id="a", tool_name="t")]
    )
    assert contents[0].parts[0].function_response.response == {"output": [1, 2]}


def test_response_skips_thoughts_and_counts_thinking_as_output() -> None:
    reply = from_gemini_response(
        gemini_response(
            [
                {"text": "Let me think...", "thought": True},
                {"text": "Done."},
                {"function_call": {"id": "f1", "name": "submit_claims", "args": {"claims": []}}},
            ],
            usage={
                "prompt_token_count": 100,
                "candidates_token_count": 20,
                "thoughts_token_count": 50,
            },
        )
    )
    assert reply.text == "Done."
    assert reply.tool_calls == (ToolCall("f1", "submit_claims", {"claims": []}),)
    assert reply.tokens.input_tokens == 100
    assert reply.tokens.output_tokens == 70
    assert reply.tokens.thinking_tokens == 50


def test_empty_response_is_a_permanent_error() -> None:
    blocked = types.GenerateContentResponse.model_validate(
        {"candidates": [], "prompt_feedback": {"block_reason": "SAFETY"}}
    )
    with pytest.raises(PermanentProviderError, match="SAFETY"):
        from_gemini_response(blocked)


def test_generate_disables_automatic_calls_and_forces_the_tool() -> None:
    sdk = RecordingSdk(gemini_response([{"text": "ok"}]))
    client = GeminiClient(
        api_key="test-key", model="m", timeout_seconds=5, temperature=None, sdk_client=sdk
    )

    client.generate(system="sys", messages=[], tools=[TOOL], required_tool="submit_claims")

    config = sdk.requests[0]["config"]
    assert sdk.requests[0]["model"] == "m"
    assert config.system_instruction == "sys"
    assert config.temperature is None
    assert config.automatic_function_calling.disable is True
    assert config.tools[0].function_declarations[0].name == "submit_claims"
    calling = config.tool_config.function_calling_config
    assert calling.mode == types.FunctionCallingConfigMode.ANY
    assert calling.allowed_function_names == ["submit_claims"]


def test_no_required_tool_means_no_tool_config() -> None:
    sdk = RecordingSdk(gemini_response([{"text": "ok"}]))
    client = GeminiClient(
        api_key="test-key", model="m", timeout_seconds=5, temperature=0.0, sdk_client=sdk
    )
    client.generate(system="s", messages=[], tools=[TOOL])
    assert sdk.requests[0]["config"].tool_config is None


def test_timeout_is_in_milliseconds_and_sdk_retries_are_off() -> None:
    options = gemini_http_options(30)
    assert options.timeout == 30_000
    assert options.retry_options.attempts == 1


def client_error(code: int) -> genai_errors.APIError:
    cls = genai_errors.ServerError if code >= 500 else genai_errors.ClientError
    return cls(code, {"error": {"code": code, "message": "boom", "status": "X"}}, None)


@pytest.mark.parametrize(
    ("sdk_error", "expected"),
    [
        (client_error(429), TransientProviderError),
        (client_error(500), TransientProviderError),
        (client_error(503), TransientProviderError),
        (client_error(401), ProviderConfigError),
        (client_error(403), ProviderConfigError),
        (client_error(400), PermanentProviderError),
        (client_error(404), PermanentProviderError),
        (httpx.ReadTimeout("slow"), ProviderTimeoutError),
        (httpx2.ConnectTimeout("slow"), ProviderTimeoutError),
        (httpx.ConnectError("down"), TransientProviderError),
        (httpx2.ReadError("reset"), TransientProviderError),
    ],
)
def test_sdk_errors_are_mapped(sdk_error: Exception, expected: type) -> None:
    assert type(map_gemini_error(sdk_error)) is expected


def test_generate_raises_our_error_not_the_sdk_error() -> None:
    sdk = RecordingSdk(httpx.ReadTimeout("slow"))
    client = GeminiClient(
        api_key="test-key", model="m", timeout_seconds=5, temperature=None, sdk_client=sdk
    )
    with pytest.raises(ProviderTimeoutError):
        client.generate(system="s", messages=[], tools=[])
