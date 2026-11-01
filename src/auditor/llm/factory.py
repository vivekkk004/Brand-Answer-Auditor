"""Build the right client for a provider from Settings."""

from auditor.config import Settings
from auditor.enums import Provider
from auditor.llm.errors import ProviderConfigError
from auditor.llm.gemini_client import GeminiClient
from auditor.llm.groq_client import GroqClient
from auditor.llm.openai_client import OpenAIClient
from auditor.llm.types import LLMClient


def build_client(provider: Provider, settings: Settings, model: str | None = None) -> LLMClient:
    """Return a client for `provider`. `model` defaults to VERIFIER_MODEL.

    Missing settings fail here, before any request, as a config error. Messages name the
    variable to set and never include a key's value.
    """
    model_id = model if model is not None else settings.verifier_model
    if not model_id:
        raise ProviderConfigError("no model ID given: set VERIFIER_MODEL")

    common = {
        "model": model_id,
        "timeout_seconds": settings.llm_timeout_seconds,
        "temperature": settings.llm_temperature,
    }
    if provider == Provider.GEMINI:
        if settings.gemini_api_key is None:
            raise ProviderConfigError("GEMINI_API_KEY is not set")
        return GeminiClient(api_key=settings.gemini_api_key.get_secret_value(), **common)
    if provider == Provider.OPENAI:
        if settings.openai_api_key is None:
            raise ProviderConfigError("OPENAI_API_KEY is not set")
        return OpenAIClient(api_key=settings.openai_api_key.get_secret_value(), **common)
    if provider == Provider.GROQ:
        if settings.groq_api_key is None:
            raise ProviderConfigError("GROQ_API_KEY is not set")
        return GroqClient(api_key=settings.groq_api_key.get_secret_value(), **common)
    raise ProviderConfigError(f"unknown provider {provider!r}")


ANSWER_MODEL_SETTING = {
    Provider.GEMINI: "GEMINI_ANSWER_MODEL",
    Provider.OPENAI: "OPENAI_ANSWER_MODEL",
    Provider.GROQ: "GROQ_ANSWER_MODEL",
}


def build_answer_client(provider: Provider, settings: Settings) -> LLMClient:
    """The client that writes the audited answers, using that provider's answer model."""
    model_id = {
        Provider.GEMINI: settings.gemini_answer_model,
        Provider.OPENAI: settings.openai_answer_model,
        Provider.GROQ: settings.groq_answer_model,
    }[provider]
    if not model_id:
        raise ProviderConfigError(f"no answer model given: set {ANSWER_MODEL_SETTING[provider]}")
    return build_client(provider, settings, model=model_id)


def build_verifier_client(settings: Settings) -> LLMClient:
    if settings.verifier_provider is None:
        raise ProviderConfigError("no verifier provider given: set VERIFIER_PROVIDER")
    return build_client(settings.verifier_provider, settings)


def build_fallback_verifier_client(settings: Settings) -> LLMClient | None:
    """The optional second verifier, or None when VERIFIER_FALLBACK_PROVIDER is not set.

    A fallback that is the same provider and model as the main verifier would only
    repeat the same failure, so that is rejected as a config error.
    """
    provider = settings.verifier_fallback_provider
    if provider is None:
        return None
    model = settings.verifier_fallback_model
    if not model:
        raise ProviderConfigError("no fallback model given: set VERIFIER_FALLBACK_MODEL")
    if provider == settings.verifier_provider and model == settings.verifier_model:
        raise ProviderConfigError(
            "the fallback verifier is the same as the main one: "
            "change VERIFIER_FALLBACK_PROVIDER or VERIFIER_FALLBACK_MODEL"
        )
    return build_client(provider, settings, model=model)
