"""What the model may send to the tools, and what the verifier returns.

The argument models use extra="forbid": an unexpected field usually means the model
misunderstood the tool, and silently dropping it would hide that mistake.
"""

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from auditor.enums import ClaimAttribute, ClaimLabel, ErrorType
from auditor.llm.types import Message, TokenUsage


class ListKnownBrandsArgs(BaseModel):
    """list_known_brands takes no arguments."""

    model_config = ConfigDict(extra="forbid")


class GetBrandFactsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brand_id: str = Field(min_length=1, max_length=64)


class SubmittedClaim(BaseModel):
    """One claim as the model submits it.

    There are no character offsets here on purpose: models count characters badly, so
    the model gives an exact quote and code finds where it is (validator.py).
    """

    model_config = ConfigDict(extra="forbid")

    quote: str = Field(min_length=1, max_length=1000)
    brand_id: str = Field(min_length=1, max_length=64)
    product: str | None = Field(default=None, max_length=200)
    attribute: ClaimAttribute
    label: ClaimLabel
    fact_ids: list[str] = Field(default_factory=list)
    rationale: str = Field(min_length=1, max_length=300)


class SubmitClaimsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claims: list[SubmittedClaim]


@dataclass(frozen=True)
class ValidatedClaim:
    """A claim that passed every check, with offsets computed by code:
    answer_text[start:end] == quote."""

    quote: str
    start: int
    end: int
    brand_id: str
    product: str | None
    attribute: ClaimAttribute
    label: ClaimLabel
    fact_ids: tuple[str, ...]
    rationale: str


@dataclass(frozen=True)
class VerificationResult:
    """The outcome of verifying one answer.

    ok=True means `claims` passed validation (it may be empty: an answer can have no
    claims). ok=False means nothing should be saved, and `error_type` says why.
    `exchanges` is the whole conversation, kept for debugging and review.
    """

    ok: bool
    claims: tuple[ValidatedClaim, ...]
    model: str
    prompt_version: str
    turns: int
    tokens: TokenUsage
    latency_ms: float
    error_type: ErrorType | None = None
    error_detail: str | None = None
    timed_out: bool = False
    exchanges: tuple[Message, ...] = ()
