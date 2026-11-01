"""What an audit run should do. Validated once, stored on the run as JSON."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from auditor.catalogue.schema import ID_PATTERN
from auditor.enums import Provider


class RunConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Prompts are picked by category; prompt_ids narrows that to a subset.
    category: str = Field(pattern=ID_PATTERN, max_length=64)
    prompt_ids: list[str] | None = Field(default=None, min_length=1, max_length=50)
    # At most two providers: enough to compare assistants, small enough to stay cheap.
    answer_providers: list[Provider] = Field(min_length=1, max_length=3)
    # Repeats measure how stable the answers are; 5 keeps a demo run affordable.
    repeats: int = Field(default=3, ge=1, le=5)
    agent_version: Literal["v1", "v2"] = "v1"
    # A hard cap on model calls (answers + verification turns), so a run cannot overspend.
    max_model_calls: int = Field(default=500, ge=1, le=5000)

    @field_validator("answer_providers", "prompt_ids")
    @classmethod
    def _no_duplicates(cls, values: list | None) -> list | None:
        if values is not None and len(set(values)) != len(values):
            raise ValueError("must not contain duplicates")
        return values
