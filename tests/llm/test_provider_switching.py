"""Choosing between Gemini, OpenAI and Groq through settings alone (no network)."""

import pytest

from auditor.config import Settings
from auditor.enums import Provider
from auditor.llm.errors import ProviderConfigError
from auditor.llm.factory import (
    build_answer_client,
    build_client,
    build_fallback_verifier_client,
    build_verifier_client,
)
from auditor.llm.gemini_client import GeminiClient
from auditor.llm.groq_client import GroqClient
from auditor.llm.openai_client import OpenAIClient

ALL_KEYS = {"gemini_api_key": "test-key", "openai_api_key": "test-key", "groq_api_key": "test-key"}
CLIENT_TYPE = {
    Provider.GEMINI: GeminiClient,
    Provider.OPENAI: OpenAIClient,
    Provider.GROQ: GroqClient,
}


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


def settings(**values) -> Settings:
    return Settings(_env_file=None, database_url="sqlite://", **values)


@pytest.mark.parametrize("provider", list(Provider))
def test_each_provider_is_built_on_its_own(provider: Provider) -> None:
    # Only this provider's key is set: each one works without the others.
    key_field = f"{provider.value}_api_key"
    client = build_client(provider, settings(verifier_model="model-x", **{key_field: "test-key"}))
    assert type(client) is CLIENT_TYPE[provider]
    assert client.model == "model-x"


def test_groq_needs_its_own_key_and_never_shows_it() -> None:
    with pytest.raises(ProviderConfigError, match="GROQ_API_KEY") as error:
        build_client(Provider.GROQ, settings(verifier_model="m", openai_api_key="test-key"))
    assert "test-key" not in str(error.value)


@pytest.mark.parametrize("provider", list(Provider))
def test_verifier_switches_with_verifier_provider(provider: Provider) -> None:
    client = build_verifier_client(
        settings(verifier_provider=provider.value, verifier_model="v", **ALL_KEYS)
    )
    assert type(client) is CLIENT_TYPE[provider]


def test_each_answer_provider_uses_its_own_answer_model() -> None:
    config = settings(
        gemini_answer_model="g-model",
        openai_answer_model="o-model",
        groq_answer_model="q-model",
        **ALL_KEYS,
    )
    built = {provider: build_answer_client(provider, config) for provider in Provider}
    assert {p: (type(c), c.model) for p, c in built.items()} == {
        Provider.GEMINI: (GeminiClient, "g-model"),
        Provider.OPENAI: (OpenAIClient, "o-model"),
        Provider.GROQ: (GroqClient, "q-model"),
    }


def test_groq_answers_need_groq_answer_model() -> None:
    with pytest.raises(ProviderConfigError, match="GROQ_ANSWER_MODEL"):
        build_answer_client(Provider.GROQ, settings(**ALL_KEYS))


def test_groq_settings_are_read_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_ANSWER_MODEL", "q-model")
    monkeypatch.setenv("VERIFIER_PROVIDER", "groq")
    config = settings()
    assert config.groq_api_key.get_secret_value() == "test-key"
    assert "test-key" not in repr(config)  # SecretStr hides it
    assert (config.groq_answer_model, config.verifier_provider) == ("q-model", Provider.GROQ)


# --- Fallback verifier ---


def test_no_fallback_is_built_when_none_is_configured() -> None:
    assert build_fallback_verifier_client(settings(**ALL_KEYS)) is None


def test_fallback_verifier_is_built_from_its_own_settings() -> None:
    client = build_fallback_verifier_client(
        settings(
            verifier_provider="groq",
            verifier_model="v",
            verifier_fallback_provider="gemini",
            verifier_fallback_model="g-fallback",
            **ALL_KEYS,
        )
    )
    assert type(client) is GeminiClient
    assert client.model == "g-fallback"


def test_fallback_needs_a_model() -> None:
    with pytest.raises(ProviderConfigError, match="VERIFIER_FALLBACK_MODEL"):
        build_fallback_verifier_client(settings(verifier_fallback_provider="openai", **ALL_KEYS))


def test_fallback_needs_its_providers_key() -> None:
    with pytest.raises(ProviderConfigError, match="GROQ_API_KEY"):
        build_fallback_verifier_client(
            settings(verifier_fallback_provider="groq", verifier_fallback_model="q")
        )


def test_fallback_identical_to_the_main_verifier_is_rejected() -> None:
    with pytest.raises(ProviderConfigError, match="same as the main one"):
        build_fallback_verifier_client(
            settings(
                verifier_provider="openai",
                verifier_model="same",
                verifier_fallback_provider="openai",
                verifier_fallback_model="same",
                **ALL_KEYS,
            )
        )
