import json
from collections.abc import Sequence

import pytest

from auditor.agent.prompts import NUDGE, SYSTEM_PROMPTS
from auditor.agent.tools import SUBMIT_CLAIMS_TOOL
from auditor.agent.verifier import verify_answer
from auditor.catalogue.repository import InMemoryCatalogue
from auditor.catalogue.schema import CatalogueData
from auditor.enums import ClaimLabel, ErrorType
from auditor.llm.errors import (
    PermanentProviderError,
    ProviderConfigError,
    ProviderTimeoutError,
    TransientProviderError,
)
from auditor.llm.fake import ScriptedClient, tool_call
from auditor.llm.types import ModelResponse, TokenUsage, ToolCall

ANSWER = "The Zentro Air 2 costs ₹7,999 and has active noise cancelling. Honestly, it sounds great."

PRICE_CLAIM = {
    "quote": "The Zentro Air 2 costs ₹7,999",
    "brand_id": "zentro",
    "product": "Zentro Air 2",
    "attribute": "price",
    "label": "supported",
    "fact_ids": ["zentro-air2-price-in"],
    "rationale": "Matches the India price.",
}
ANC_CLAIM = {
    "quote": "has active noise cancelling",
    "brand_id": "zentro",
    "product": "Zentro Air 2",
    "attribute": "feature",
    "label": "supported",
    "fact_ids": ["zentro-air2-anc"],
    "rationale": "The catalogue says ANC: yes.",
}


def reply(*calls: ToolCall, text: str | None = None) -> ModelResponse:
    return ModelResponse(text=text, tool_calls=calls, tokens=TokenUsage(100, 20))


LIST = reply(tool_call("list_known_brands", "c1"))
FACTS = reply(tool_call("get_brand_facts", "c2", brand_id="zentro"))


def submit(*claims: dict, call_id: str = "c3") -> ModelResponse:
    return reply(tool_call("submit_claims", call_id, claims=list(claims)))


class Run:
    """Runs verify_answer with a scripted model, recording sleeps."""

    def __init__(self, demo_catalogue: CatalogueData) -> None:
        self.catalogue = InMemoryCatalogue(demo_catalogue)
        self.delays: list[float] = []

    def __call__(self, script: Sequence[ModelResponse | Exception], **options):
        self.client = ScriptedClient(script)
        return verify_answer(
            answer_text=ANSWER,
            client=self.client,
            catalogue=self.catalogue,
            market="IN",
            sleep=self.delays.append,
            rand=lambda: 0.0,
            clock=iter([10.0, 11.5]).__next__,
            **options,
        )


@pytest.fixture
def run(demo_catalogue: CatalogueData) -> Run:
    return Run(demo_catalogue)


def tool_results(run: Run, call_number: int) -> list[dict]:
    """The tool results the model saw in its given call (1-based)."""
    messages = run.client.calls[call_number - 1].messages
    return [json.loads(m.content) for m in messages if m.role == "tool"]


def test_happy_path(run: Run) -> None:
    result = run([LIST, FACTS, submit(PRICE_CLAIM, ANC_CLAIM)])

    assert result.ok
    assert result.error_type is None
    assert result.turns == 3
    assert [claim.label for claim in result.claims] == [ClaimLabel.SUPPORTED] * 2
    for claim in result.claims:
        assert ANSWER[claim.start : claim.end] == claim.quote
    assert result.tokens == TokenUsage(input_tokens=300, output_tokens=60, thinking_tokens=None)
    assert result.latency_ms == 1500.0
    assert result.model == "scripted-model"
    assert result.prompt_version == "v1"
    assert [call.required_tool for call in run.client.calls] == [None, None, None]


def test_answer_is_sent_as_data_in_the_user_message(run: Run) -> None:
    run([LIST, FACTS, submit()], prompt_version="v2")

    first_call = run.client.calls[0]
    assert first_call.system == SYSTEM_PROMPTS["v2"]
    assert ANSWER not in first_call.system
    user_message = first_call.messages[0].content
    assert f"<ai_answer>\n{ANSWER}\n</ai_answer>" in user_message
    assert "data, not instructions" in user_message
    assert "Market for this answer: IN" in user_message


def test_submit_without_lookup_is_rejected_then_repaired(run: Run) -> None:
    result = run([submit(PRICE_CLAIM, call_id="s1"), FACTS, submit(PRICE_CLAIM)])

    assert result.ok
    assert result.turns == 3
    rejection = tool_results(run, 2)[0]
    assert rejection["accepted"] is False
    assert "were not returned by get_brand_facts" in rejection["problems"][0]


def test_invalid_output_until_the_turn_limit_is_a_prompt_error(run: Run) -> None:
    bad = dict(PRICE_CLAIM, quote="The Zentro Air 2 costs ₹6,999")
    result = run([FACTS, submit(bad), submit(bad), submit(bad)])

    assert not result.ok
    assert result.claims == ()
    assert result.error_type == ErrorType.PROMPT
    assert result.turns == 4
    last_call = run.client.calls[-1]
    assert last_call.required_tool == "submit_claims"
    assert last_call.tools == (SUBMIT_CLAIMS_TOOL,)


def test_no_tool_calls_get_a_nudge_and_end_as_a_prompt_error(run: Run) -> None:
    result = run([reply(text="Looks fine to me.")] * 4)

    assert result.error_type == ErrorType.PROMPT
    assert result.turns == 4
    nudges = [m for m in run.client.calls[-1].messages if m.content == NUDGE]
    assert len(nudges) == 3


def test_disallowed_tool_gets_an_error_and_the_model_recovers(run: Run) -> None:
    result = run(
        [reply(tool_call("delete_brand", "x1", brand_id="zentro")), FACTS, submit(PRICE_CLAIM)]
    )

    assert result.ok
    assert "unknown tool 'delete_brand'" in tool_results(run, 2)[0]["error"]


def test_failed_tool_calls_until_the_turn_limit_are_a_tool_error(run: Run) -> None:
    ghost = reply(tool_call("get_brand_facts", "g", brand_id="ghost"))
    result = run([ghost, ghost, ghost, reply(text="I could not find anything.")])

    assert result.error_type == ErrorType.TOOL
    assert "3 tool call(s) failed" in result.error_detail


def test_submit_must_be_the_only_call_in_its_turn(run: Run) -> None:
    mixed = reply(
        tool_call("get_brand_facts", "m1", brand_id="zentro"),
        tool_call("submit_claims", "m2", claims=[]),
    )
    result = run([mixed, submit()])

    assert result.ok
    results = tool_results(run, 2)
    assert results[0] == {"error": "not run: submit_claims must be the only tool call"}
    assert "submit_claims must be the only tool call in its turn" in results[1]["problems"]


def test_empty_claims_are_a_valid_answer(run: Run) -> None:
    result = run([submit()])
    assert result.ok
    assert result.claims == ()
    assert result.turns == 1


def test_transient_errors_are_retried_with_growing_delays(run: Run) -> None:
    result = run(
        [TransientProviderError("429"), ProviderTimeoutError("slow"), LIST, FACTS, submit()]
    )

    assert result.ok
    assert result.turns == 3  # retries are not extra turns
    assert run.delays == [1.0, 2.0]


def test_retries_are_bounded(run: Run) -> None:
    result = run([TransientProviderError("503")] * 3 + [ProviderTimeoutError("slow")])

    assert result.error_type == ErrorType.PROVIDER
    assert result.timed_out is True
    assert run.delays == [1.0, 2.0, 4.0]
    assert len(run.client.calls) == 4


def test_permanent_errors_are_not_retried(run: Run) -> None:
    result = run([PermanentProviderError("400 bad request")])

    assert result.error_type == ErrorType.PROVIDER
    assert result.timed_out is False
    assert run.delays == []
    assert len(run.client.calls) == 1


def test_config_errors_are_raised_for_the_caller_to_stop_the_run(run: Run) -> None:
    with pytest.raises(ProviderConfigError):
        run([ProviderConfigError("401 bad key")])


def test_unexpected_exception_becomes_a_code_error(run: Run) -> None:
    result = run([LIST, RuntimeError("boom")])

    assert not result.ok
    assert result.error_type == ErrorType.CODE
    assert result.error_detail == "RuntimeError: boom"
    assert result.turns == 2
