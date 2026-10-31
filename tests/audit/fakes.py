"""Fake answer writers and a fake verifier, so audit tests never call a model API."""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from auditor.config import Settings
from auditor.db import models as db
from auditor.enums import Provider
from auditor.llm.fake import tool_call
from auditor.llm.types import Message, ModelResponse, TokenUsage, ToolSpec

GEMINI_TEXT = "The Zentro Air 2 costs ₹6,999 and the Kovalt Pulse is also good."
OPENAI_TEXT = "I would pick the Zentro Air 2."

WRITER_TOKENS = TokenUsage(input_tokens=10, output_tokens=40)
VERIFIER_TOKENS = TokenUsage(input_tokens=50, output_tokens=10)

CONTRADICTED_PRICE = {
    "quote": "The Zentro Air 2 costs ₹6,999",
    "brand_id": "zentro",
    "product": "Zentro Air 2",
    "attribute": "price",
    "label": "contradicted",
    "fact_ids": ["zentro-air2-price-in"],
    "rationale": "The catalogue price in India is 7999 INR.",
}


class FakeWriter:
    """Answers every prompt with the same text. `script` items run first, in order:
    an Exception is raised, a string is returned as the answer text."""

    def __init__(self, model: str, text: str, script: Sequence[Exception | str] = ()) -> None:
        self.model = model
        self.text = text
        self.script = list(script)
        self.prompts: list[str] = []

    def generate(
        self,
        *,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        required_tool: str | None = None,
    ) -> ModelResponse:
        assert system == "" and not tools  # audit answers: no system prompt, no tools
        self.prompts.append(messages[0].content)
        item = self.script.pop(0) if self.script else self.text
        if isinstance(item, Exception):
            raise item
        return ModelResponse(text=item, tokens=WRITER_TOKENS)


class FakeVerifier:
    """Plays the agent's side in two turns: fetch Zentro facts, then submit.

    It submits the contradicted price claim when the answer contains it, and an empty
    list otherwise.
    """

    model = "fake-verifier"

    def __init__(self) -> None:
        self.calls = 0

    def generate(
        self,
        *,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        required_tool: str | None = None,
    ) -> ModelResponse:
        self.calls += 1
        if not any(message.role == "tool" for message in messages):
            call = tool_call("get_brand_facts", "f1", brand_id="zentro")
        else:
            claims = [CONTRADICTED_PRICE] if "₹6,999" in messages[0].content else []
            call = tool_call("submit_claims", "s1", claims=claims)
        return ModelResponse(text=None, tool_calls=(call,), tokens=VERIFIER_TOKENS)


class Writers:
    """answer_client_for(provider) for process_run, with one FakeWriter per provider."""

    def __init__(self, **scripts: Sequence[Exception | str]) -> None:
        self.by_provider = {
            Provider.GEMINI: FakeWriter("gemini-answer", GEMINI_TEXT, scripts.get("gemini", ())),
            Provider.OPENAI: FakeWriter("openai-answer", OPENAI_TEXT, scripts.get("openai", ())),
        }

    def __call__(self, provider: Provider) -> FakeWriter:
        return self.by_provider[provider]

    @property
    def total_calls(self) -> int:
        return sum(len(writer.prompts) for writer in self.by_provider.values())


def make_settings(**values: Any) -> Settings:
    defaults: dict[str, Any] = {
        "database_url": "sqlite://",
        "verifier_provider": "gemini",
        "verifier_model": "fake-verifier",
        "gemini_answer_model": "gemini-answer",
        "openai_answer_model": "openai-answer",
        "gemini_api_key": "test-key",
        "openai_api_key": "test-key",
    }
    defaults.update(values)
    return Settings(_env_file=None, **defaults)


def create_run(
    session_factory: sessionmaker[Session], config: dict[str, Any], key: str = "run-1"
) -> uuid.UUID:
    """Add a queued run (and its API client, if new) and return the run ID."""
    with session_factory.begin() as session:
        client = session.query(db.ApiClient).filter_by(name="test-client").one_or_none()
        if client is None:
            client = db.ApiClient(name="test-client", key_hash="0" * 64)
            session.add(client)
            session.flush()
        run = db.AuditRun(
            client_id=client.id,
            idempotency_key=key,
            request_hash="0" * 64,
            config=config,
            max_model_calls=config.get("max_model_calls", 500),
        )
        session.add(run)
        session.flush()
        return run.id
