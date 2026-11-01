import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

from auditor.catalogue.loader import PROMPTS_FILE, load_catalogue, load_prompts, seed_database
from auditor.catalogue.schema import CatalogueData
from auditor.config import Settings
from auditor.db.models import Base
from auditor.db.session import make_engine, make_session_factory

REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = REPO_ROOT / "data" / "demo"


@pytest.fixture(autouse=True)
def _ignore_local_env_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """Never read the developer's .env in tests. Code under test (for example the CLI)
    builds Settings() itself; without this, real keys or a VERIFIER_PROVIDER in .env
    would change test results, and a test could even reach a real model API."""
    monkeypatch.setitem(Settings.model_config, "env_file", None)


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


@pytest.fixture
def seeded(
    session_factory: sessionmaker[Session], demo_catalogue: CatalogueData
) -> sessionmaker[Session]:
    """A database with the demo catalogue and prompts loaded."""
    with session_factory.begin() as session:
        seed_database(session, demo_catalogue, load_prompts(DEMO_DIR / PROMPTS_FILE))
    return session_factory
