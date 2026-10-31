import pytest

from auditor.config import Settings


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # A developer's real environment must not leak into these tests.
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


def make_settings(**values) -> Settings:
    return Settings(_env_file=None, database_url="sqlite://", **values)


def test_defaults_leave_model_ids_empty() -> None:
    settings = make_settings()
    assert settings.verifier_provider is None
    assert settings.verifier_model == ""
    assert settings.agent_max_turns == 4
    assert settings.llm_temperature == 0.0
    assert settings.input_token_price_per_million is None


def test_temperature_can_be_turned_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_TEMPERATURE", "none")
    assert make_settings().llm_temperature is None


def test_empty_env_value_means_not_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERIFIER_PROVIDER", "")
    assert make_settings().verifier_provider is None


def test_api_keys_are_hidden_when_printed() -> None:
    settings = make_settings(gemini_api_key="test-key")
    assert "test-key" not in repr(settings)
    assert settings.gemini_api_key is not None
    assert settings.gemini_api_key.get_secret_value() == "test-key"


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("postgres://u:p@db:5432/a", "postgresql+psycopg://u:p@db:5432/a"),
        ("postgresql://u:p@db:5432/a", "postgresql+psycopg://u:p@db:5432/a"),
        ("postgresql+psycopg://u:p@db:5432/a", "postgresql+psycopg://u:p@db:5432/a"),
        ("sqlite:///./auditor.db", "sqlite:///./auditor.db"),
    ],
)
def test_postgres_urls_get_the_psycopg_driver(given: str, expected: str) -> None:
    assert Settings(_env_file=None, database_url=given).database_url == expected


def test_more_than_four_agent_turns_is_rejected() -> None:
    with pytest.raises(ValueError):
        make_settings(agent_max_turns=5)
