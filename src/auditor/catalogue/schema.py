"""Catalogue types: brands, facts and prompts, with strict validation."""

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, ConfigDict, Field, model_validator

from auditor.enums import FactAttribute

ID_PATTERN = r"^[a-z0-9][a-z0-9-]*$"
MARKET_PATTERN = r"^[A-Z]{2}$"

# A price is only meaningful with its market's currency (SPEC 3.3).
CURRENCY_BY_MARKET = {"IN": "INR", "US": "USD"}


class Brand(BaseModel):
    model_config = ConfigDict(frozen=True)

    brand_id: str = Field(pattern=ID_PATTERN, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    aliases: tuple[str, ...] = ()


class Fact(BaseModel):
    model_config = ConfigDict(frozen=True)

    fact_id: str = Field(pattern=ID_PATTERN, max_length=100)
    brand_id: str = Field(pattern=ID_PATTERN, max_length=64)
    product: str | None = Field(default=None, max_length=200)
    attribute: FactAttribute
    value: str = Field(min_length=1, max_length=200)
    unit: str | None = Field(default=None, max_length=32)
    market: str | None = Field(default=None, pattern=MARKET_PATTERN)
    conditions: str | None = Field(default=None, max_length=200)
    valid_from: date | None = None
    source_url: str | None = Field(default=None, pattern=r"^https?://", max_length=500)

    @model_validator(mode="after")
    def _value_fits_attribute(self) -> "Fact":
        problem = attribute_problem(self)
        if problem is not None:
            raise ValueError(problem)
        return self


class Prompt(BaseModel):
    model_config = ConfigDict(frozen=True)

    prompt_id: str = Field(pattern=ID_PATTERN, max_length=64)
    text: str = Field(min_length=1, max_length=2000)
    market: str | None = Field(default=None, pattern=MARKET_PATTERN)


@dataclass(frozen=True)
class CatalogueData:
    brands: tuple[Brand, ...]
    facts: tuple[Fact, ...]


def attribute_problem(fact: Fact) -> str | None:
    """Return why a fact's value/unit/market do not fit its attribute, or None if they do."""
    match fact.attribute:
        case FactAttribute.PRICE:
            if fact.market is None:
                return "a price needs a market"
            currency = CURRENCY_BY_MARKET.get(fact.market)
            if currency is None:
                return f"no currency is known for market {fact.market}"
            if fact.unit != currency:
                return f"a price in market {fact.market} must use unit {currency}"
            if not _is_positive_number(fact.value):
                return "a price must be a positive number"
        case FactAttribute.BATTERY:
            if fact.unit != "hours":
                return "battery life must use unit hours"
            if not _is_positive_number(fact.value):
                return "battery life must be a positive number"
            if fact.conditions is None:
                return "battery life needs conditions, for example 'earbuds only, ANC off'"
        case FactAttribute.WARRANTY:
            if fact.unit != "months":
                return "a warranty must use unit months"
            if not fact.value.isdigit() or int(fact.value) == 0:
                return "a warranty must be a whole number of months"
            if fact.market is None:
                return "a warranty needs a market"
        case FactAttribute.ANC:
            if fact.value not in ("yes", "no"):
                return "anc must be 'yes' or 'no'"
            if fact.unit is not None:
                return "anc takes no unit"
        case FactAttribute.WATER_RESISTANCE:
            if re.fullmatch(r"IP[X0-9][0-9]", fact.value) is None:
                return "water resistance must be an IP code such as IPX4 or IP67"
            if fact.unit is not None:
                return "water resistance takes no unit"
        case FactAttribute.RELEASE_YEAR:
            if not fact.value.isdigit() or not 2000 <= int(fact.value) <= 2100:
                return "release year must be a year between 2000 and 2100"
            if fact.unit is not None:
                return "release year takes no unit"
    return None


def _is_positive_number(value: str) -> bool:
    try:
        number = Decimal(value)
    except InvalidOperation:
        return False
    return number.is_finite() and number > 0
