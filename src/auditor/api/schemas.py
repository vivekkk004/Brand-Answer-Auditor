"""Request and response bodies. Requests reject unknown fields (extra="forbid"), so a typo
in a field name is an error instead of being silently ignored."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from auditor.catalogue.schema import MARKET_PATTERN

# --- Requests ---
# POST /v1/audit-runs takes auditor.audit.run_config.RunConfig directly.


class VerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=20_000)
    market: str | None = Field(default=None, pattern=MARKET_PATTERN)
    prompt_version: Literal["v1", "v2"] = "v1"


class ReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["confirmed", "dismissed"]
    note: str | None = Field(default=None, max_length=2000)


# --- Responses ---


class ClaimOut(BaseModel):
    id: uuid.UUID
    quote: str
    start: int
    end: int
    brand_id: str
    product: str | None
    attribute: str
    label: str
    fact_ids: list[str]
    rationale: str


class AnswerOut(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID | None
    prompt_id: str | None
    provider: str | None
    model: str | None
    repeat_index: int | None
    market: str | None
    text: str | None
    status: str
    error_type: str | None
    error_message: str | None
    brands_mentioned: list[str]
    verifier_model: str | None
    prompt_version: str | None
    verification_turns: int | None
    verification_latency_ms: float | None
    timed_out: bool
    usage: dict[str, Any]
    claims: list[ClaimOut]
    exchanges: list[dict[str, Any]] | None
    created_at: datetime


class RunOut(BaseModel):
    id: uuid.UUID
    status: str
    config: dict[str, Any]
    model_calls: int
    max_model_calls: int
    metrics: dict[str, Any] | None
    failure_reason: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class ReviewItemOut(BaseModel):
    id: uuid.UUID
    status: str
    note: str | None
    created_at: datetime
    resolved_at: datetime | None
    answer_id: uuid.UUID
    claim: ClaimOut


class ReviewItemList(BaseModel):
    items: list[ReviewItemOut]
    limit: int
    offset: int
