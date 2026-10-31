"""Provider errors, sorted by what the caller should do about them."""


class ProviderError(Exception):
    """Base class: a model API call failed."""


class TransientProviderError(ProviderError):
    """May succeed if tried again: rate limit (429), server error (5xx), timeout, or a
    connection problem. Only these are retried."""


class ProviderTimeoutError(TransientProviderError):
    """The request took longer than LLM_TIMEOUT_SECONDS. Kept separate so failures can
    report timed_out."""


class PermanentProviderError(ProviderError):
    """Will fail the same way again (for example 400, 404, a blocked or empty response),
    so retrying only wastes time and money."""


class ProviderConfigError(ProviderError):
    """Our setup is wrong: missing key or model ID, or credentials rejected (401/403).
    Retrying cannot help; a person has to fix the configuration."""


def error_for_status(status_code: int, message: str) -> ProviderError:
    """Map an HTTP status code to our error type. Shared by both providers."""
    if status_code == 429 or status_code >= 500:
        return TransientProviderError(message)
    if status_code in (401, 403):
        return ProviderConfigError(message)
    return PermanentProviderError(message)
