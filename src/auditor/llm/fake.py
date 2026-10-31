"""A scripted stand-in for a real model, so tests never call a model API."""

from collections.abc import Sequence
from dataclasses import dataclass

from auditor.llm.types import Message, ModelResponse, ToolCall, ToolSpec


@dataclass(frozen=True)
class RecordedCall:
    system: str
    messages: tuple[Message, ...]
    tools: tuple[ToolSpec, ...]
    required_tool: str | None


class ScriptedClient:
    """Returns pre-written responses, or raises pre-written exceptions, in order.

    Every call is recorded, so a test can check exactly what the agent sent.
    Running out of script is a test bug, so it fails loudly.
    """

    def __init__(
        self, script: Sequence[ModelResponse | Exception], model: str = "scripted-model"
    ) -> None:
        self.model = model
        self._script = list(script)
        self.calls: list[RecordedCall] = []

    def generate(
        self,
        *,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        required_tool: str | None = None,
    ) -> ModelResponse:
        self.calls.append(RecordedCall(system, tuple(messages), tuple(tools), required_tool))
        if not self._script:
            raise AssertionError("ScriptedClient ran out of scripted responses")
        item = self._script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def tool_call(name: str, call_id: str = "call-1", **arguments: object) -> ToolCall:
    """Shorthand for tests: tool_call("get_brand_facts", brand_id="zentro")."""
    return ToolCall(id=call_id, name=name, arguments=dict(arguments))
