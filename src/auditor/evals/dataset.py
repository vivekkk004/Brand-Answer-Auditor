"""The hand-labelled eval set: strict loading, gold offsets, and a fingerprint.

Gold offsets are computed with the SAME locate_quote the validator uses for the model's
claims. If the two used different rules, a perfect prediction of a repeated sentence
could land on a different occurrence than its gold claim and be scored as wrong.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from auditor.agent.validator import locate_quote
from auditor.catalogue.repository import Catalogue
from auditor.enums import ClaimLabel

DATASET_FILE = "eval_set.json"
Split = Literal["dev", "holdout"]


class DatasetError(ValueError):
    """The eval set is broken. `problems` lists every problem found, not just the first."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("\n".join(problems))
        self.problems = problems


# --- The file format ---


class _GoldClaimIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quote: str = Field(min_length=1)
    brand_id: str
    label: ClaimLabel
    fact_ids: list[str] = []
    # Why the claim has this label (for example "market trap"). For people, not scoring.
    note: str | None = None

    @model_validator(mode="after")
    def _decided_labels_cite_facts(self) -> "_GoldClaimIn":
        # The same rule the agent must follow (SPEC 3.4).
        if self.label != ClaimLabel.UNKNOWN and not self.fact_ids:
            raise ValueError(f"a {self.label} claim must cite at least one fact ID")
        return self


class _AnswerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer_id: str = Field(min_length=1)
    split: Split
    prompt_id: str
    market: str | None
    text: str = Field(min_length=1)
    gold_claims: list[_GoldClaimIn]


class _DatasetIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    answers: list[_AnswerIn]


# --- The loaded dataset ---


@dataclass(frozen=True)
class GoldSpan:
    start: int
    end: int
    quote: str
    brand_id: str
    label: ClaimLabel
    fact_ids: tuple[str, ...]


@dataclass(frozen=True)
class DatasetAnswer:
    answer_id: str
    split: Split
    prompt_id: str
    market: str | None
    text: str
    gold: tuple[GoldSpan, ...]


@dataclass(frozen=True)
class Dataset:
    version: str
    # SHA-256 of the dataset's content. Two reports can only be compared if they were
    # scored against exactly the same gold labels.
    sha256: str
    answers: tuple[DatasetAnswer, ...]

    def select(self, split: str, answer_ids: list[str] | None = None) -> list[DatasetAnswer]:
        """The answers of one split, optionally narrowed to some answer IDs."""
        if split not in ("dev", "holdout"):
            raise DatasetError([f"unknown split {split!r}; use dev or holdout"])
        chosen = [answer for answer in self.answers if answer.split == split]
        if answer_ids is None:
            return chosen
        by_id = {answer.answer_id: answer for answer in chosen}
        unknown = [answer_id for answer_id in answer_ids if answer_id not in by_id]
        if unknown:
            raise DatasetError([f"unknown answer IDs in split {split!r}: {unknown}"])
        return [by_id[answer_id] for answer_id in answer_ids]


def load_dataset(path: Path, catalogue: Catalogue, prompt_ids: set[str]) -> Dataset:
    """Load and check the eval set. Raises DatasetError listing every problem.

    Rejected: invalid JSON, unknown fields, bad labels, duplicate answer IDs, unknown
    prompt IDs, quotes that cannot be located, unknown brands and unknown fact IDs.
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DatasetError([f"{path.name}: invalid JSON: {exc}"]) from exc
    try:
        parsed = _DatasetIn.model_validate(raw)
    except ValidationError as exc:
        raise DatasetError(
            [
                f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
                for error in exc.errors()
            ]
        ) from exc

    brand_ids = {brand.brand_id for brand in catalogue.list_brands()}
    fact_ids = {fact.fact_id for b in brand_ids for fact in catalogue.get_brand_facts(b)}
    problems: list[str] = []
    answers: list[DatasetAnswer] = []
    seen_answer_ids: set[str] = set()

    for answer in parsed.answers:
        where = answer.answer_id
        if where in seen_answer_ids:
            problems.append(f"{where}: duplicate answer_id")
        seen_answer_ids.add(where)
        if answer.prompt_id not in prompt_ids:
            problems.append(f"{where}: unknown prompt_id {answer.prompt_id!r}")

        gold: list[GoldSpan] = []
        used_spans: set[tuple[int, int]] = set()
        cursor = 0
        for number, claim in enumerate(answer.gold_claims, start=1):
            at = f"{where} claim {number}"
            span = locate_quote(answer.text, claim.quote, used_spans, cursor)
            if span is None:
                problems.append(
                    f"{at}: quote not found in the answer text (or every occurrence is "
                    f"already used by an earlier gold claim): {claim.quote!r}"
                )
            else:
                used_spans.add(span)
                cursor = span[1]
            if claim.brand_id not in brand_ids:
                problems.append(f"{at}: unknown brand_id {claim.brand_id!r}")
            for fact_id in claim.fact_ids:
                if fact_id not in fact_ids:
                    problems.append(f"{at}: unknown fact ID {fact_id!r}")
            if span is not None:
                gold.append(
                    GoldSpan(
                        start=span[0],
                        end=span[1],
                        quote=claim.quote,
                        brand_id=claim.brand_id,
                        label=claim.label,
                        fact_ids=tuple(claim.fact_ids),
                    )
                )
        answers.append(
            DatasetAnswer(
                answer_id=answer.answer_id,
                split=answer.split,
                prompt_id=answer.prompt_id,
                market=answer.market,
                text=answer.text,
                gold=tuple(gold),
            )
        )

    if problems:
        raise DatasetError(problems)
    return Dataset(version=parsed.version, sha256=fingerprint(raw), answers=tuple(answers))


def fingerprint(raw: Any) -> str:
    """SHA-256 of the content, not the file bytes: re-indenting the file or changing its
    line endings (Windows vs Linux checkouts) must not change the fingerprint."""
    canonical = json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
