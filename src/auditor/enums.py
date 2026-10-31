"""Fixed sets of values used across the app. Stored in the database as plain strings."""

from enum import StrEnum


class Provider(StrEnum):
    GEMINI = "gemini"
    OPENAI = "openai"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    # Stopped early because the model-call budget ran out; metrics cover what was done.
    PARTIAL = "partial"
    FAILED = "failed"


class AnswerStatus(StrEnum):
    PENDING = "pending"
    GENERATION_FAILED = "generation_failed"
    VERIFICATION_FAILED = "verification_failed"
    VERIFIED = "verified"


class ClaimLabel(StrEnum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    UNKNOWN = "unknown"


class ClaimAttribute(StrEnum):
    """What a claim in an answer is about (SPEC 3.1)."""

    PRICE = "price"
    BATTERY = "battery"
    FEATURE = "feature"
    WARRANTY = "warranty"
    WATER_RESISTANCE = "water_resistance"
    RELEASE_YEAR = "release_year"
    COMPARISON = "comparison"


class FactAttribute(StrEnum):
    """What a catalogue fact records (SPEC 4.6)."""

    PRICE = "price"
    BATTERY = "battery"
    ANC = "anc"
    WATER_RESISTANCE = "water_resistance"
    WARRANTY = "warranty"
    RELEASE_YEAR = "release_year"


class ErrorType(StrEnum):
    PROVIDER = "provider"
    PROMPT = "prompt"
    TOOL = "tool"
    DATA = "data"
    CONFIG = "config"
    CODE = "code"


class ReviewStatus(StrEnum):
    OPEN = "open"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"
