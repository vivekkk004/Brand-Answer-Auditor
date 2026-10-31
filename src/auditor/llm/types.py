"""Provider-neutral types: the agent only ever sees these, never an SDK object.

Each provider client converts these to and from its own SDK's format, so the agent
code is the same for Gemini, OpenAI and the scripted fake used in tests.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

Role = Literal["user", "assistant", "tool"]


@dataclass(frozen=True)
class ToolSpec:
    """A tool the model may call. `parameters` is a plain JSON schema."""

    name: str
    description: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class ToolCall:
    """The model asking to run one tool.

    If the model sent arguments that are not a JSON object, they are kept as
    {"_unparsed": "<raw text>"} so the agent can report the problem back to the model
    instead of crashing.
    """

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class Message:
    """One turn in the conversation.

    - user: `content` is the text.
    - assistant: `content` and/or `tool_calls`; `raw` holds the provider's original turn,
      which Gemini needs replayed unchanged (it carries hidden thought signatures).
    - tool: `content` is the tool result as JSON text, answering `tool_call_id`/`tool_name`.
    """

    role: Role
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None
    tool_name: str | None = None
    raw: Any = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class TokenUsage:
    """Token counts from the provider. None means the provider did not report them;
    we never estimate. `output_tokens` includes `thinking_tokens` (both are billed as output).
    """

    input_tokens: int | None = None
    output_tokens: int | None = None
    thinking_tokens: int | None = None


@dataclass(frozen=True)
class ModelResponse:
    text: str | None
    tool_calls: tuple[ToolCall, ...] = ()
    tokens: TokenUsage = TokenUsage()
    raw: Any = field(default=None, compare=False, repr=False)

    def to_message(self) -> Message:
        """The assistant turn to append to the conversation."""
        return Message(
            role="assistant", content=self.text or "", tool_calls=self.tool_calls, raw=self.raw
        )


class LLMClient(Protocol):
    model: str

    def generate(
        self,
        *,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        required_tool: str | None = None,
    ) -> ModelResponse:
        """Make ONE model request (no retries here; see retry.py).

        `required_tool` forces the model to call exactly that tool; the agent uses it
        on its last turn so the model must submit instead of browsing.
        Raises the errors in errors.py, never an SDK error.
        """
        ...
