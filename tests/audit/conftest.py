from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session, sessionmaker

from auditor.catalogue.loader import PROMPTS_FILE, load_prompts, seed_database
from auditor.catalogue.schema import CatalogueData
from auditor.config import Settings

from ..conftest import DEMO_DIR


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # A developer's real keys or model settings must not leak into these tests.
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


@pytest.fixture
def seeded(
    session_factory: sessionmaker[Session], demo_catalogue: CatalogueData
) -> Iterator[sessionmaker[Session]]:
    """A database with the demo catalogue and prompts loaded."""
    with session_factory.begin() as session:
        seed_database(session, demo_catalogue, load_prompts(DEMO_DIR / PROMPTS_FILE))
    yield session_factory
