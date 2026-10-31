import pytest

from auditor.config import Settings
from auditor.enums import Provider
from auditor.llm.errors import ProviderConfigError, TransientProviderError
from auditor.llm.factory import build_client
from auditor.llm.fake import ScriptedClient, tool_call
from auditor.llm.gemini_client import GeminiClient
from auditor.llm.openai_client import OpenAIClient
from auditor.llm.types import Message, ModelResponse


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


def settings(**values) -> Settings:
    return Settings(_env_file=None, database_url="sqlite://", **values)


@pytest.mark.parametrize(
    ("provider", "key_field", "expected"),
    [
        (Provider.GEMINI, "gemini_api_key", GeminiClient),
        (Provider.OPENAI, "openai_api_key", OpenAIClient),
    ],
)
def test_factory_builds_the_right_client(
    provider: Provider, key_field: str, expected: type
) -> None:
    client = build_client(provider, settings(verifier_model="model-x", **{key_field: "test-key"}))
    assert isinstance(client, expected)
    assert client.model == "model-x"


def test_explicit_model_overrides_verifier_model() -> None:
    client = build_client(
        Provider.OPENAI, settings(verifier_model="a", openai_api_key="test-key"), model="b"
    )
    assert client.model == "b"


@pytest.mark.parametrize(
    ("provider", "missing"),
    [(Provider.GEMINI, "GEMINI_API_KEY"), (Provider.OPENAI, "OPENAI_API_KEY")],
)
def test_factory_fails_without_a_key(provider: Provider, missing: str) -> None:
    with pytest.raises(ProviderConfigError, match=missing):
        build_client(provider, settings(verifier_model="model-x"))


def test_factory_fails_without_a_model_and_never_shows_the_key() -> None:
    with pytest.raises(ProviderConfigError, match="VERIFIER_MODEL") as error:
        build_client(Provider.GEMINI, settings(gemini_api_key="test-key"))
    assert "test-key" not in str(error.value)


def test_scripted_client_replays_in_order_and_records_calls() -> None:
    first = ModelResponse(text=None, tool_calls=(tool_call("list_known_brands"),))
    client = ScriptedClient([first, TransientProviderError("429")])
    messages = [Message(role="user", content="hi")]

    assert client.generate(system="s", messages=messages, tools=[]) is first
    with pytest.raises(TransientProviderError):
        client.generate(system="s", messages=messages, tools=[], required_tool="submit_claims")
    with pytest.raises(AssertionError, match="ran out"):
        client.generate(system="s", messages=messages, tools=[])

    assert len(client.calls) == 3
    assert client.calls[1].required_tool == "submit_claims"
    assert client.calls[0].messages == (Message(role="user", content="hi"),)
