"""The agent's tools: their JSON schemas and the code that runs the read-only ones.

The schemas are written by hand, without "$ref": both providers accept plain inline
schemas, and a reader can see exactly what the model is shown. A test checks that they
match the Pydantic models in schemas.py.
"""

import json
from typing import Any

from pydantic import ValidationError

from auditor.agent.schemas import GetBrandFactsArgs, ListKnownBrandsArgs
from auditor.catalogue.repository import Catalogue
from auditor.catalogue.schema import Fact
from auditor.enums import ClaimAttribute, ClaimLabel
from auditor.llm.types import UNPARSED_ARGUMENTS_KEY, Message, ToolCall, ToolSpec

LIST_KNOWN_BRANDS = "list_known_brands"
GET_BRAND_FACTS = "get_brand_facts"
SUBMIT_CLAIMS = "submit_claims"

# Only read-only tools are run by the executor. submit_claims is the final answer and is
# handled by the verifier itself. Anything else the model asks for is refused.
ALLOWED_TOOLS = frozenset({LIST_KNOWN_BRANDS, GET_BRAND_FACTS})

LIST_KNOWN_BRANDS_TOOL = ToolSpec(
    name=LIST_KNOWN_BRANDS,
    description="List every brand in the fact catalogue with its ID, name and aliases.",
    parameters={"type": "object", "properties": {}, "additionalProperties": False},
)

GET_BRAND_FACTS_TOOL = ToolSpec(
    name=GET_BRAND_FACTS,
    description=(
        "Return every catalogue fact for one brand. Each fact has a fact_id to cite. "
        "Only facts returned by this tool may be cited."
    ),
    parameters={
        "type": "object",
        "properties": {
            "brand_id": {"type": "string", "description": "A brand_id from list_known_brands."}
        },
        "required": ["brand_id"],
        "additionalProperties": False,
    },
)

SUBMIT_CLAIMS_TOOL = ToolSpec(
    name=SUBMIT_CLAIMS,
    description=(
        "Submit your final list of claims. Call it once, on its own. "
        "Use an empty list if the answer makes no checkable claims."
    ),
    parameters={
        "type": "object",
        "properties": {
            "claims": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "quote": {
                            "type": "string",
                            "description": "Exact text copied from the answer, character for "
                            "character. The smallest clause that holds the fact.",
                        },
                        "brand_id": {"type": "string"},
                        "product": {
                            "type": ["string", "null"],
                            "description": "Product name as in the catalogue; null if the "
                            "claim is about the whole brand.",
                        },
                        "attribute": {"type": "string", "enum": [a.value for a in ClaimAttribute]},
                        "label": {"type": "string", "enum": [label.value for label in ClaimLabel]},
                        "fact_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Facts that decide the label. Required for "
                            "supported and contradicted.",
                        },
                        "rationale": {
                            "type": "string",
                            "description": "One or two sentences for a human reviewer.",
                        },
                    },
                    "required": ["quote", "brand_id", "attribute", "label", "rationale"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["claims"],
        "additionalProperties": False,
    },
)

AGENT_TOOLS = (LIST_KNOWN_BRANDS_TOOL, GET_BRAND_FACTS_TOOL, SUBMIT_CLAIMS_TOOL)


class ToolExecutor:
    """Runs the read-only tools for ONE answer.

    It never raises. A bad call (unknown tool, bad arguments, unknown brand, or even a
    crash inside a tool) comes back to the model as {"error": ...}, so the model can
    correct itself on its next turn. Errors are counted so the verifier can tell a
    "tools kept failing" failure apart from a "bad final answer" one.

    It also records every fact ID it has returned. A claim may only cite those IDs:
    that is how we prove the model looked a fact up instead of inventing it.
    """

    def __init__(self, catalogue: Catalogue) -> None:
        self._catalogue = catalogue
        self.seen_fact_ids: set[str] = set()
        self.error_count = 0

    def execute(self, call: ToolCall) -> dict[str, Any]:
        if call.name not in ALLOWED_TOOLS:
            return self._error(
                f"unknown tool {call.name!r}; use {LIST_KNOWN_BRANDS}, {GET_BRAND_FACTS} "
                f"or {SUBMIT_CLAIMS}"
            )
        if UNPARSED_ARGUMENTS_KEY in call.arguments:
            return self._error("arguments were not a valid JSON object")
        try:
            if call.name == LIST_KNOWN_BRANDS:
                ListKnownBrandsArgs.model_validate(call.arguments)
                return self._list_known_brands()
            args = GetBrandFactsArgs.model_validate(call.arguments)
            return self._get_brand_facts(args.brand_id)
        except ValidationError as exc:
            return self._error(f"invalid arguments: {_summarise(exc)}")
        except Exception as exc:  # a tool must never crash the agent loop
            return self._error(f"{call.name} failed: {type(exc).__name__}")

    def _list_known_brands(self) -> dict[str, Any]:
        return {
            "brands": [
                {"brand_id": brand.brand_id, "name": brand.name, "aliases": list(brand.aliases)}
                for brand in self._catalogue.list_brands()
            ]
        }

    def _get_brand_facts(self, brand_id: str) -> dict[str, Any]:
        if self._catalogue.get_brand(brand_id) is None:
            return self._error(f"unknown brand_id {brand_id!r}; call {LIST_KNOWN_BRANDS}")
        facts = self._catalogue.get_brand_facts(brand_id)
        self.seen_fact_ids.update(fact.fact_id for fact in facts)
        return {"brand_id": brand_id, "facts": [_fact_payload(fact) for fact in facts]}

    def _error(self, message: str) -> dict[str, Any]:
        self.error_count += 1
        return {"error": message}


def tool_result_message(call: ToolCall, result: dict[str, Any]) -> Message:
    return Message(
        role="tool", content=json.dumps(result), tool_call_id=call.id, tool_name=call.name
    )


def _fact_payload(fact: Fact) -> dict[str, Any]:
    return {
        "fact_id": fact.fact_id,
        "product": fact.product,
        "attribute": fact.attribute.value,
        "value": fact.value,
        "unit": fact.unit,
        "market": fact.market,
        "conditions": fact.conditions,
        "valid_from": fact.valid_from.isoformat() if fact.valid_from else None,
    }


def _summarise(exc: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(part) for part in error['loc']) or 'arguments'}: {error['msg']}"
        for error in exc.errors()
    )
