"""Read-only access to the catalogue, from memory or from the database.

Both implementations return results in the same order (sorted in Python, not by the
database), so they can be swapped freely and compared in tests.
"""

from collections import defaultdict
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from auditor.catalogue.schema import Brand, CatalogueData, Fact
from auditor.db import models as db


class Catalogue(Protocol):
    def list_brands(self) -> list[Brand]: ...

    def get_brand(self, brand_id: str) -> Brand | None: ...

    def get_brand_facts(self, brand_id: str) -> list[Fact]:
        """Facts for one brand, sorted by fact ID. Empty for an unknown brand."""
        ...


class InMemoryCatalogue:
    def __init__(self, data: CatalogueData) -> None:
        self._brands = {brand.brand_id: brand for brand in data.brands}
        facts_by_brand: dict[str, list[Fact]] = defaultdict(list)
        for fact in data.facts:
            facts_by_brand[fact.brand_id].append(fact)
        self._facts_by_brand = {
            brand_id: sorted(facts, key=lambda fact: fact.fact_id)
            for brand_id, facts in facts_by_brand.items()
        }

    def list_brands(self) -> list[Brand]:
        return sorted(self._brands.values(), key=lambda brand: brand.brand_id)

    def get_brand(self, brand_id: str) -> Brand | None:
        return self._brands.get(brand_id)

    def get_brand_facts(self, brand_id: str) -> list[Fact]:
        return list(self._facts_by_brand.get(brand_id, []))


class SqlCatalogue:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_brands(self) -> list[Brand]:
        aliases: dict[str, list[str]] = defaultdict(list)
        for row in self._session.scalars(select(db.BrandAlias)):
            aliases[row.brand_id].append(row.alias)
        brands = [
            Brand(brand_id=row.id, name=row.name, aliases=tuple(sorted(aliases[row.id])))
            for row in self._session.scalars(select(db.Brand))
        ]
        return sorted(brands, key=lambda brand: brand.brand_id)

    def get_brand(self, brand_id: str) -> Brand | None:
        row = self._session.get(db.Brand, brand_id)
        if row is None:
            return None
        aliases = self._session.scalars(
            select(db.BrandAlias.alias).where(db.BrandAlias.brand_id == brand_id)
        )
        return Brand(brand_id=row.id, name=row.name, aliases=tuple(sorted(aliases)))

    def get_brand_facts(self, brand_id: str) -> list[Fact]:
        rows = self._session.scalars(select(db.BrandFact).where(db.BrandFact.brand_id == brand_id))
        return sorted((fact_from_row(row) for row in rows), key=lambda fact: fact.fact_id)


def fact_from_row(row: db.BrandFact) -> Fact:
    return Fact(
        fact_id=row.id,
        brand_id=row.brand_id,
        product=row.product,
        attribute=row.attribute,
        value=row.value,
        unit=row.unit,
        market=row.market,
        conditions=row.conditions,
        valid_from=row.valid_from,
        source_url=row.source_url,
    )


def fact_to_row(fact: Fact) -> db.BrandFact:
    return db.BrandFact(
        id=fact.fact_id,
        brand_id=fact.brand_id,
        product=fact.product,
        attribute=fact.attribute,
        value=fact.value,
        unit=fact.unit,
        market=fact.market,
        conditions=fact.conditions,
        valid_from=fact.valid_from,
        source_url=fact.source_url,
    )
