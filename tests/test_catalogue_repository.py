from sqlalchemy.orm import Session, sessionmaker

from auditor.catalogue.loader import seed_database
from auditor.catalogue.repository import InMemoryCatalogue, SqlCatalogue
from auditor.catalogue.schema import CatalogueData


def test_sql_and_in_memory_catalogues_return_the_same_data(
    session_factory: sessionmaker[Session], demo_catalogue: CatalogueData
) -> None:
    with session_factory.begin() as session:
        seed_database(session, demo_catalogue, [])

    memory = InMemoryCatalogue(demo_catalogue)
    # A fresh session, so every value is read back from the database.
    with session_factory() as session:
        sql = SqlCatalogue(session)
        assert sql.list_brands() == memory.list_brands()
        total_facts = 0
        for brand in memory.list_brands():
            assert sql.get_brand(brand.brand_id) == memory.get_brand(brand.brand_id)
            assert sql.get_brand_facts(brand.brand_id) == memory.get_brand_facts(brand.brand_id)
            total_facts += len(memory.get_brand_facts(brand.brand_id))

    assert total_facts == len(demo_catalogue.facts)


def test_unknown_brand_gives_none_and_no_facts(
    session_factory: sessionmaker[Session], demo_catalogue: CatalogueData
) -> None:
    with session_factory.begin() as session:
        seed_database(session, demo_catalogue, [])

    with session_factory() as session:
        for catalogue in (InMemoryCatalogue(demo_catalogue), SqlCatalogue(session)):
            assert catalogue.get_brand("ghost") is None
            assert catalogue.get_brand_facts("ghost") == []
