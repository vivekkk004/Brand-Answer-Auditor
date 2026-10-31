"""App settings, read from environment variables (and a local .env file if present)."""

from decimal import Decimal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from auditor.enums import Provider


class Settings(BaseSettings):
    # env_ignore_empty: a line like `OPENAI_API_KEY=` in .env means "not set", not "".
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_ignore_empty=True, extra="ignore"
    )

    database_url: str

    gemini_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None

    # Left empty on purpose: model IDs change often, so they must be set explicitly.
    # Code that needs them raises a `config` error when they are missing.
    verifier_provider: Provider | None = None
    verifier_model: str = ""

    llm_timeout_seconds: float = Field(default=30.0, gt=0)
    llm_max_retries: int = Field(default=3, ge=0, le=10)
    agent_max_turns: int = Field(default=4, ge=1, le=4)
    # None means "do not send a temperature"; some models reject the parameter.
    llm_temperature: float | None = Field(default=0.0, ge=0, le=2)

    # USD per 1 million tokens. Cost is only reported when both are set.
    input_token_price_per_million: Decimal | None = Field(default=None, ge=0)
    output_token_price_per_million: Decimal | None = Field(default=None, ge=0)

    log_level: str = "INFO"

    @field_validator("llm_temperature", mode="before")
    @classmethod
    def _none_string_means_no_temperature(cls, value: object) -> object:
        if isinstance(value, str) and value.strip().lower() == "none":
            return None
        return value
