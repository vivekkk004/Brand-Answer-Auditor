"""Strict CSV loading of the catalogue and prompts, and seeding them into the database.

"Strict" means: exact column headers, the right number of fields on every row, every
value validated, no duplicate IDs or aliases, and no reference to an unknown brand.
The first problem stops the load, with the file name and line number in the message.
"""

import csv
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from auditor.catalogue.repository import fact_from_row, fact_to_row
from auditor.catalogue.schema import Brand, CatalogueData, Fact, Prompt
from auditor.db import models as db

BRANDS_FILE = "brands.csv"
ALIASES_FILE = "brand_aliases.csv"
FACTS_FILE = "brand_facts.csv"
PROMPTS_FILE = "prompts.csv"

BRAND_COLUMNS = ("brand_id", "name")
ALIAS_COLUMNS = ("brand_id", "alias")
FACT_COLUMNS = (
    "fact_id",
    "brand_id",
    "product",
    "attribute",
    "value",
    "unit",
    "market",
    "conditions",
    "valid_from",
    "source_url",
)
PROMPT_COLUMNS = ("prompt_id", "text", "market")


class CatalogueError(ValueError):
    """Catalogue or prompt data is invalid."""


def load_catalogue(directory: Path) -> CatalogueData:
    names = _load_brand_names(directory / BRANDS_FILE)
    aliases = _load_aliases(directory / ALIASES_FILE, names)
    facts = _load_facts(directory / FACTS_FILE, names)
    brands = tuple(
        Brand(brand_id=brand_id, name=name, aliases=tuple(sorted(aliases[brand_id])))
        for brand_id, name in sorted(names.items())
    )
    return CatalogueData(brands=brands, facts=facts)


def load_prompts(path: Path) -> tuple[Prompt, ...]:
    prompts: dict[str, Prompt] = {}
    for line, row in _read_rows(path, PROMPT_COLUMNS):
        prompt = _validate(Prompt, path, line, row)
        if prompt.prompt_id in prompts:
            raise _error(path, line, f"duplicate prompt_id {prompt.prompt_id!r}")
        prompts[prompt.prompt_id] = prompt
    return tuple(sorted(prompts.values(), key=lambda prompt: prompt.prompt_id))


def seed_database(
    session: Session, catalogue: CatalogueData, prompts: Sequence[Prompt]
) -> dict[str, int]:
    """Insert the rows that are missing and return how many of each kind were inserted.

    Rows that already exist must match exactly. Facts are immutable (SPEC 4.6), so a seed
    that would change an existing row is refused instead of overwriting it. The caller
    owns the transaction.
    """
    inserted = {"brands": 0, "aliases": 0, "facts": 0, "prompts": 0}

    for brand in catalogue.brands:
        existing = session.get(db.Brand, brand.brand_id)
        if existing is None:
            session.add(db.Brand(id=brand.brand_id, name=brand.name))
            inserted["brands"] += 1
        elif existing.name != brand.name:
            raise CatalogueError(f"brand {brand.brand_id!r} already exists with another name")
    # Brands must be in the database before aliases and facts point at them.
    session.flush()

    alias_owners = {row.alias: row.brand_id for row in session.scalars(select(db.BrandAlias))}
    for brand in catalogue.brands:
        for alias in brand.aliases:
            owner = alias_owners.get(alias)
            if owner is None:
                session.add(db.BrandAlias(brand_id=brand.brand_id, alias=alias))
                inserted["aliases"] += 1
            elif owner != brand.brand_id:
                raise CatalogueError(f"alias {alias!r} already belongs to brand {owner!r}")

    for fact in catalogue.facts:
        existing_fact = session.get(db.BrandFact, fact.fact_id)
        if existing_fact is None:
            session.add(fact_to_row(fact))
            inserted["facts"] += 1
        elif fact_from_row(existing_fact) != fact:
            raise CatalogueError(
                f"fact {fact.fact_id!r} already exists with different content; "
                "facts are immutable, so give the new version a new ID"
            )

    for prompt in prompts:
        existing_prompt = session.get(db.Prompt, prompt.prompt_id)
        if existing_prompt is None:
            session.add(db.Prompt(id=prompt.prompt_id, text=prompt.text, market=prompt.market))
            inserted["prompts"] += 1
        elif (existing_prompt.text, existing_prompt.market) != (prompt.text, prompt.market):
            raise CatalogueError(f"prompt {prompt.prompt_id!r} already exists with other content")

    session.flush()
    return inserted


def _load_brand_names(path: Path) -> dict[str, str]:
    names: dict[str, str] = {}
    seen_names: set[str] = set()
    for line, row in _read_rows(path, BRAND_COLUMNS):
        brand = _validate(Brand, path, line, row)
        if brand.brand_id in names:
            raise _error(path, line, f"duplicate brand_id {brand.brand_id!r}")
        if brand.name.casefold() in seen_names:
            raise _error(path, line, f"duplicate brand name {brand.name!r}")
        names[brand.brand_id] = brand.name
        seen_names.add(brand.name.casefold())
    return names


def _load_aliases(path: Path, names: dict[str, str]) -> dict[str, list[str]]:
    aliases: dict[str, list[str]] = {brand_id: [] for brand_id in names}
    # An alias must not clash with any brand name or other alias, ignoring case,
    # or a mention in an answer could belong to two brands.
    taken = {name.casefold() for name in names.values()}
    for line, row in _read_rows(path, ALIAS_COLUMNS):
        brand_id, alias = row["brand_id"], row["alias"]
        if brand_id not in names:
            raise _error(path, line, f"unknown brand_id {brand_id!r}")
        if alias is None:
            raise _error(path, line, "alias is empty")
        if alias.casefold() in taken:
            raise _error(path, line, f"alias {alias!r} is already used")
        aliases[brand_id].append(alias)
        taken.add(alias.casefold())
    return aliases


def _load_facts(path: Path, names: dict[str, str]) -> tuple[Fact, ...]:
    facts: dict[str, Fact] = {}
    for line, row in _read_rows(path, FACT_COLUMNS):
        fact = _validate(Fact, path, line, row)
        if fact.brand_id not in names:
            raise _error(path, line, f"unknown brand_id {fact.brand_id!r}")
        if fact.fact_id in facts:
            raise _error(path, line, f"duplicate fact_id {fact.fact_id!r}")
        facts[fact.fact_id] = fact
    return tuple(sorted(facts.values(), key=lambda fact: fact.fact_id))


def _read_rows(path: Path, columns: tuple[str, ...]) -> list[tuple[int, dict[str, str | None]]]:
    """Read a CSV file into (line number, row) pairs. Blank cells become None."""
    if not path.is_file():
        raise CatalogueError(f"{path.name}: file not found")
    rows = []
    # utf-8-sig: accept files saved by Excel, which start with a byte-order mark.
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None or tuple(reader.fieldnames) != columns:
            raise CatalogueError(
                f"{path.name}: expected columns {list(columns)}, got {reader.fieldnames}"
            )
        for row in reader:
            # DictReader puts extra fields under the key None and fills missing ones with None.
            if None in row or None in row.values():
                raise _error(path, reader.line_num, f"expected {len(columns)} fields")
            rows.append(
                (reader.line_num, {key: value.strip() or None for key, value in row.items()})
            )
    return rows


def _validate[M: BaseModel](model: type[M], path: Path, line: int, row: dict) -> M:
    try:
        return model.model_validate(row)
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(part) for part in error['loc']) or 'row'}: {error['msg']}"
            for error in exc.errors()
        )
        raise _error(path, line, details) from exc


def _error(path: Path, line: int, message: str) -> CatalogueError:
    return CatalogueError(f"{path.name} line {line}: {message}")
