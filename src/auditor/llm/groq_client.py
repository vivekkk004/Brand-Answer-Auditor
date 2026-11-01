"""Groq client: Groq's API speaks the OpenAI Chat Completions format, so this is the
OpenAI client pointed at Groq's endpoint. Requests, tool calls, token counts and error
mapping (429/5xx retried, 401/403 config, timeouts) are exactly the OpenAI client's.
"""

from typing import Any

from auditor.llm.openai_client import OpenAIClient

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class GroqClient(OpenAIClient):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float,
        temperature: float | None,
        sdk_client: Any = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
            temperature=temperature,
            sdk_client=sdk_client,
            base_url=GROQ_BASE_URL,
            provider_label="Groq",
        )
