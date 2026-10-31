"""Database tables (SQLAlchemy 2 ORM). See SPEC.md section 6.6."""

import uuid
from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from auditor.enums import (
    AnswerStatus,
    ClaimAttribute,
    ClaimLabel,
    ErrorType,
    FactAttribute,
    Provider,
    ReviewStatus,
    RunStatus,
)

# Predictable constraint names, so migrations can drop them on every database.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def utc_now() -> datetime:
    return datetime.now(UTC)


def str_enum(enum_cls: type[StrEnum]) -> Enum:
    """Store a StrEnum as its plain string value in a VARCHAR column.

    Plain strings (not a native database enum type) keep migrations simple:
    adding a new value later needs no ALTER TYPE.
    """
    return Enum(
        enum_cls,
        native_enum=False,
        length=32,
        values_callable=lambda cls: [member.value for member in cls],
        validate_strings=True,
    )


# --- Catalogue (shared by all clients) ---


class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)


class BrandAlias(Base):
    __tablename__ = "brand_aliases"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"), index=True)
    alias: Mapped[str] = mapped_column(String(200), unique=True)


class BrandFact(Base):
    """One catalogue fact. Immutable: a changed fact gets a new ID."""

    __tablename__ = "brand_facts"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"), index=True)
    product: Mapped[str | None] = mapped_column(String(200))
    attribute: Mapped[FactAttribute] = mapped_column(str_enum(FactAttribute))
    value: Mapped[str] = mapped_column(String(200))
    unit: Mapped[str | None] = mapped_column(String(32))
    market: Mapped[str | None] = mapped_column(String(8))
    conditions: Mapped[str | None] = mapped_column(String(200))
    valid_from: Mapped[date | None] = mapped_column(Date)
    source_url: Mapped[str | None] = mapped_column(String(500))


class Prompt(Base):
    __tablename__ = "prompts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    # Runs select their prompts by category (for example "earbuds").
    category: Mapped[str] = mapped_column(String(64), index=True)
    text: Mapped[str] = mapped_column(Text)
    market: Mapped[str | None] = mapped_column(String(8))


# --- Client-owned data ---


class ApiClient(Base):
    __tablename__ = "api_clients"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    # SHA-256 hex digest of the API key. The key itself is never stored.
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuditRun(Base):
    __tablename__ = "audit_runs"
    __table_args__ = (UniqueConstraint("client_id", "idempotency_key"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("api_clients.id"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(200))
    # SHA-256 of the request body, to spot a reused key with a different body.
    request_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[RunStatus] = mapped_column(str_enum(RunStatus), default=RunStatus.QUEUED)
    # The validated RunConfig (audit/run_config.py), stored as JSON.
    config: Mapped[dict] = mapped_column(JSON)
    # Budget: model calls used so far, checked before every call (SPEC 6.4).
    max_model_calls: Mapped[int]
    model_calls: Mapped[int] = mapped_column(default=0)
    # Results of compute_run_metrics, written when the run finishes.
    metrics: Mapped[dict | None] = mapped_column(JSON)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Updated after every answer; a running run with an old heartbeat has lost its worker.
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Answer(Base):
    """One AI answer. From an audit run (run_id set) or from POST /v1/verify (run_id empty)."""

    __tablename__ = "answers"
    # One answer per prompt, model and repeat within a run. Rows without a run
    # have NULLs here, and NULLs never clash in a unique constraint.
    __table_args__ = (UniqueConstraint("run_id", "prompt_id", "model", "repeat_index"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("api_clients.id"), index=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("audit_runs.id"), index=True)
    prompt_id: Mapped[str | None] = mapped_column(ForeignKey("prompts.id"))
    provider: Mapped[Provider | None] = mapped_column(str_enum(Provider))
    model: Mapped[str | None] = mapped_column(String(200))
    repeat_index: Mapped[int | None]
    market: Mapped[str | None] = mapped_column(String(8))
    text: Mapped[str | None] = mapped_column(Text)
    status: Mapped[AnswerStatus] = mapped_column(
        str_enum(AnswerStatus), default=AnswerStatus.PENDING
    )
    error_type: Mapped[ErrorType | None] = mapped_column(str_enum(ErrorType))
    error_message: Mapped[str | None] = mapped_column(Text)
    brands_mentioned: Mapped[list[str]] = mapped_column(JSON, default=list)
    verifier_provider: Mapped[Provider | None] = mapped_column(str_enum(Provider))
    verifier_model: Mapped[str | None] = mapped_column(String(200))
    prompt_version: Mapped[str | None] = mapped_column(String(16))
    verification_turns: Mapped[int | None]
    verification_latency_ms: Mapped[float | None]
    timed_out: Mapped[bool] = mapped_column(default=False)
    # Token counts as reported by the provider, never estimated:
    # {"generation": {...}, "verification": {...}} with input/output/thinking keys.
    usage: Mapped[dict] = mapped_column(JSON, default=dict)
    # The verifier's whole conversation (messages and tool calls), for review and debugging.
    exchanges: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    answer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("answers.id"), index=True)
    quote: Mapped[str] = mapped_column(Text)
    # Computed by code, never by the model: answer.text[start_offset:end_offset] == quote.
    start_offset: Mapped[int]
    end_offset: Mapped[int]
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"))
    product: Mapped[str | None] = mapped_column(String(200))
    attribute: Mapped[ClaimAttribute] = mapped_column(str_enum(ClaimAttribute))
    label: Mapped[ClaimLabel] = mapped_column(str_enum(ClaimLabel))
    fact_ids: Mapped[list[str]] = mapped_column(JSON)
    rationale: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ReviewItem(Base):
    __tablename__ = "review_items"
    __table_args__ = (Index("ix_review_items_client_id_status", "client_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("api_clients.id"))
    claim_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("claims.id"), unique=True)
    status: Mapped[ReviewStatus] = mapped_column(str_enum(ReviewStatus), default=ReviewStatus.OPEN)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
