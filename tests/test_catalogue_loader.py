from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

from auditor.catalogue.loader import (
    PROMPTS_FILE,
    CatalogueError,
    load_catalogue,
    load_prompts,
    seed_database,
)
from auditor.catalogue.schema import CatalogueData

from .conftest import DEMO_DIR


def test_demo_catalogue_counts(demo_catalogue: CatalogueData) -> None:
    assert len(demo_catalogue.brands) == 6
    assert len(demo_catalogue.facts) == 59
    assert all(brand.aliases for brand in demo_catalogue.brands)
    # Every brand has facts, and every fact belongs to a known brand.
    brand_ids = {brand.brand_id for brand in demo_catalogue.brands}
    assert {fact.brand_id for fact in demo_catalogue.facts} == brand_ids
    assert len(load_prompts(DEMO_DIR / PROMPTS_FILE)) == 6


def append_line(path: Path, line: str) -> None:
    with path.open("a", encoding="utf-8") as file:
        file.write(line + "\n")


def replace_text(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


FACTS = "brand_facts.csv"

# Each case appends one bad row to a copy of the demo data: (file, row, expected error).
BAD_ROWS = {
    "extra field": ("brands.csv", "newbrand,New Brand,extra", "expected 2 fields"),
    "missing fields": (FACTS, "zentro-short,zentro", "expected 10 fields"),
    "duplicate brand_id": ("brands.csv", "zentro,Zentro Two", "duplicate brand_id"),
    "bad brand_id": ("brands.csv", "Bad Id,Bad Brand", "brand_id"),
    "alias for unknown brand": ("brand_aliases.csv", "ghost,Ghost Audio", "unknown brand_id"),
    "duplicate alias ignoring case": ("brand_aliases.csv", "kovalt,zentro audio", "already used"),
    "fact for unknown brand": (FACTS, "ghost-anc,ghost,Ghost 1,anc,yes,,,,,", "unknown brand_id"),
    "duplicate fact_id": (FACTS, "zentro-air2-anc,zentro,Air,anc,no,,,,,", "duplicate fact_id"),
    "unknown attribute": (FACTS, "zentro-x,zentro,Air,colour,red,,,,,", "attribute"),
    "price in wrong currency": (FACTS, "zentro-x,zentro,Air,price,99,INR,US,,,", "unit USD"),
    "price not a number": (FACTS, "zentro-x,zentro,Air,price,cheap,USD,US,,,", "positive number"),
    "battery without conditions": (FACTS, "zentro-x,zentro,Air,battery,8,hours,,,,", "conditions"),
    "bad market code": (FACTS, "zentro-x,zentro,Air,anc,yes,,usa,,,", "market"),
    "bad date": (FACTS, "zentro-x,zentro,Air,anc,yes,,,,soon,", "valid_from"),
}


@pytest.mark.parametrize("case", BAD_ROWS.keys())
def test_bad_csv_row_is_rejected(demo_copy: Path, case: str) -> None:
    file_name, row, expected_message = BAD_ROWS[case]
    append_line(demo_copy / file_name, row)
    with pytest.raises(CatalogueError, match=expected_message):
        load_catalogue(demo_copy)


def test_wrong_header_is_rejected(demo_copy: Path) -> None:
    replace_text(demo_copy / "brands.csv", "brand_id,name", "id,name")
    with pytest.raises(CatalogueError, match="expected columns"):
        load_catalogue(demo_copy)


def test_error_names_file_and_line(demo_copy: Path) -> None:
    append_line(demo_copy / "brand_facts.csv", "ghost-anc,ghost,Ghost 1,anc,yes,,,,,")
    # Header is line 1, then 59 facts, so the new row is line 61.
    with pytest.raises(CatalogueError, match=r"^brand_facts\.csv line 61: "):
        load_catalogue(demo_copy)


def test_duplicate_prompt_is_rejected(demo_copy: Path) -> None:
    append_line(demo_copy / PROMPTS_FILE, "p01,Another prompt,US")
    with pytest.raises(CatalogueError, match="duplicate prompt_id"):
        load_prompts(demo_copy / PROMPTS_FILE)


def test_seed_inserts_once_and_is_safe_to_repeat(
    session_factory: sessionmaker[Session], demo_catalogue: CatalogueData
) -> None:
    prompts = load_prompts(DEMO_DIR / PROMPTS_FILE)
    with session_factory.begin() as session:
        first = seed_database(session, demo_catalogue, prompts)
    with session_factory.begin() as session:
        second = seed_database(session, demo_catalogue, prompts)

    assert first == {"brands": 6, "aliases": 6, "facts": 59, "prompts": 6}
    assert second == {"brands": 0, "aliases": 0, "facts": 0, "prompts": 0}


def test_seed_refuses_to_change_an_existing_fact(
    session_factory: sessionmaker[Session], demo_catalogue: CatalogueData
) -> None:
    with session_factory.begin() as session:
        seed_database(session, demo_catalogue, [])

    first, *rest = demo_catalogue.facts
    changed = CatalogueData(
        brands=demo_catalogue.brands,
        facts=(first.model_copy(update={"source_url": "https://example.com/changed"}), *rest),
    )
    with session_factory.begin() as session:
        with pytest.raises(CatalogueError, match="immutable"):
            seed_database(session, changed, [])
