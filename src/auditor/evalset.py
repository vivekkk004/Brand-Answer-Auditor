"""The hand-labelled evaluation set: loading it and checking it against the catalogue."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from auditor.catalogue.repository import Catalogue
from auditor.enums import ClaimLabel


class GoldClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quote: str = Field(min_length=1)
    brand_id: str
    label: ClaimLabel
    fact_ids: list[str] = []
    # Why this claim is labelled the way it is (for example "market trap").
    note: str | None = None

    @model_validator(mode="after")
    def _decided_labels_cite_facts(self) -> "GoldClaim":
        # Same rule as the agent's output (SPEC 3.4).
        if self.label != ClaimLabel.UNKNOWN and not self.fact_ids:
            raise ValueError(f"a {self.label} claim must cite at least one fact ID")
        return self


class EvalAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer_id: str
    split: Literal["dev", "holdout"]
    prompt_id: str
    market: str | None
    text: str = Field(min_length=1)
    gold_claims: list[GoldClaim]


class EvalSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    answers: list[EvalAnswer]


def load_eval_set(path: Path) -> EvalSet:
    return EvalSet.model_validate_json(path.read_text(encoding="utf-8"))


def check_eval_set(eval_set: EvalSet, catalogue: Catalogue, prompt_ids: set[str]) -> list[str]:
    """Return every problem found. An empty list means the eval set is consistent.

    Each gold quote must appear exactly once in its answer, so its span is unambiguous.
    """
    brand_ids = {brand.brand_id for brand in catalogue.list_brands()}
    fact_ids = {
        fact.fact_id for brand_id in brand_ids for fact in catalogue.get_brand_facts(brand_id)
    }
    problems: list[str] = []
    seen_answer_ids: set[str] = set()

    for answer in eval_set.answers:
        where = answer.answer_id
        if where in seen_answer_ids:
            problems.append(f"{where}: duplicate answer_id")
        seen_answer_ids.add(where)
        if answer.prompt_id not in prompt_ids:
            problems.append(f"{where}: unknown prompt_id {answer.prompt_id!r}")

        seen_quotes: set[str] = set()
        for number, claim in enumerate(answer.gold_claims, start=1):
            at = f"{where} claim {number}"
            count = answer.text.count(claim.quote)
            if count == 0:
                problems.append(f"{at}: quote not found in answer text: {claim.quote!r}")
            elif count > 1:
                problems.append(f"{at}: quote appears {count} times; it must appear once")
            if claim.quote in seen_quotes:
                problems.append(f"{at}: same quote as an earlier claim")
            seen_quotes.add(claim.quote)
            if claim.brand_id not in brand_ids:
                problems.append(f"{at}: unknown brand_id {claim.brand_id!r}")
            for fact_id in claim.fact_ids:
                if fact_id not in fact_ids:
                    problems.append(f"{at}: unknown fact ID {fact_id!r}")
    return problems
