import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

from auditor.catalogue.loader import load_catalogue
from auditor.catalogue.schema import CatalogueData
from auditor.db.models import Base
from auditor.db.session import make_engine, make_session_factory

REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = REPO_ROOT / "data" / "demo"


@pytest.fixture
def demo_catalogue() -> CatalogueData:
    return load_catalogue(DEMO_DIR)


@pytest.fixture
def demo_copy(tmp_path: Path) -> Path:
    """A private copy of the demo data that a test may break."""
    return Path(shutil.copytree(DEMO_DIR, tmp_path / "demo"))


@pytest.fixture
def session_factory(tmp_path: Path) -> Iterator[sessionmaker[Session]]:
    engine = make_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    Base.metadata.create_all(engine)
    yield make_session_factory(engine)
    engine.dispose()
