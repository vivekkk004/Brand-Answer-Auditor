"""Groq client tests. No request leaves the machine: the SDK is replaced by a recorder,
or only constructed (building an SDK client makes no network call)."""

import httpx
import openai
import pytest

from auditor.llm.errors import (
    PermanentProviderError,
    ProviderConfigError,
    ProviderTimeoutError,
    TransientProviderError,
)
from auditor.llm.groq_client import GROQ_BASE_URL, GroqClient
from auditor.llm.openai_client import OpenAIClient, map_openai_error
from auditor.llm.types import Message, ToolSpec

from .test_openai_client import RecordingSdk, completion

TOOL = ToolSpec("get_brand_facts", "Facts for one brand.", {"type": "object", "properties": {}})
REQUEST = httpx.Request("POST", f"{GROQ_BASE_URL}/chat/completions")


def groq(sdk: RecordingSdk, temperature: float | None = 0.0) -> GroqClient:
    return GroqClient(
        api_key="test-key",
        model="groq-model",
        timeout_seconds=5,
        temperature=temperature,
        sdk_client=sdk,
    )


def status_error(cls: type[openai.APIStatusError], status: int) -> openai.APIStatusError:
    return cls("boom", response=httpx.Response(status, request=REQUEST), body=None)


def test_groq_points_the_sdk_at_groqs_endpoint_with_no_sdk_retries() -> None:
    client = GroqClient(api_key="test-key", model="m", timeout_seconds=7, temperature=0.0)
    sdk = client._client
    assert str(sdk.base_url).rstrip("/") == "https://api.groq.com/openai/v1"
    assert sdk.max_retries == 0  # our retry loop is the only one (SPEC 4.8)
    assert sdk.timeout == 7


def test_openai_client_still_uses_the_openai_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    client = OpenAIClient(api_key="test-key", model="m", timeout_seconds=5, temperature=0.0)
    assert str(client._client.base_url).rstrip("/") == "https://api.openai.com/v1"


def test_groq_sends_an_openai_format_request() -> None:
    sdk = RecordingSdk(completion({"role": "assistant", "content": "hi"}))
    groq(sdk).generate(
        system="Be careful.",
        messages=[Message(role="user", content="Check this.")],
        tools=[TOOL],
        required_tool="get_brand_facts",
    )
    (request,) = sdk.requests
    assert request["model"] == "groq-model"
    assert request["messages"][0] == {"role": "system", "content": "Be careful."}
    assert request["tools"][0]["function"]["name"] == "get_brand_facts"
    assert request["tool_choice"] == {"type": "function", "function": {"name": "get_brand_facts"}}
    assert request["temperature"] == 0.0


def test_groq_reads_tool_calls_and_token_usage() -> None:
    sdk = RecordingSdk(
        completion(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "get_brand_facts",
                            "arguments": '{"brand_id": "zentro"}',
                        },
                    }
                ],
            },
            usage={"prompt_tokens": 120, "completion_tokens": 15, "total_tokens": 135},
        )
    )
    response = groq(sdk).generate(system="s", messages=[], tools=[TOOL])
    (call,) = response.tool_calls
    assert (call.name, call.arguments) == ("get_brand_facts", {"brand_id": "zentro"})
    assert (response.tokens.input_tokens, response.tokens.output_tokens) == (120, 15)


@pytest.mark.parametrize(
    ("sdk_error", "expected", "message_start"),
    [
        (openai.APITimeoutError(request=REQUEST), ProviderTimeoutError, "Groq request timed out"),
        (openai.APIConnectionError(request=REQUEST), TransientProviderError, "Groq connection"),
        (status_error(openai.RateLimitError, 429), TransientProviderError, "Groq 429"),
        (status_error(openai.InternalServerError, 503), TransientProviderError, "Groq 503"),
        (status_error(openai.AuthenticationError, 401), ProviderConfigError, "Groq 401"),
        (status_error(openai.BadRequestError, 400), PermanentProviderError, "Groq 400"),
    ],
)
def test_groq_errors_are_mapped_and_named(
    sdk_error: openai.OpenAIError, expected: type, message_start: str
) -> None:
    with pytest.raises(expected) as raised:
        groq(RecordingSdk(sdk_error)).generate(system="s", messages=[], tools=[])
    assert type(raised.value) is expected
    assert str(raised.value).startswith(message_start)


def test_openai_error_messages_are_unchanged() -> None:
    error = map_openai_error(status_error(openai.RateLimitError, 429))
    assert str(error).startswith("OpenAI 429")


def test_groq_empty_choices_is_a_permanent_groq_error() -> None:
    sdk = RecordingSdk(completion({"role": "assistant", "content": "x"}))
    sdk.result = sdk.result.model_copy(update={"choices": []})
    with pytest.raises(PermanentProviderError, match="Groq returned no choices"):
        groq(sdk).generate(system="s", messages=[], tools=[])
