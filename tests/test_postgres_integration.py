"""PostgreSQL-only behaviour, on the real migrations.

Skipped unless TEST_POSTGRES_URL points at an EMPTY database, for example
postgresql+psycopg://auditor:auditor@localhost:5432/auditor_test. The tests migrate it
up, and migrate it back down to empty at the end.
"""

import os
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session, sessionmaker

from auditor.audit.pipeline import claim_next_run, process_run, queued_run_query
from auditor.catalogue.loader import PROMPTS_FILE, load_catalogue, load_prompts, seed_database
from auditor.db import models as db
from auditor.db.session import make_engine, make_session_factory
from auditor.enums import RunStatus

from .audit.fakes import FakeVerifier, Writers, create_run, make_settings
from .conftest import DEMO_DIR, REPO_ROOT

pytestmark = pytest.mark.skipif(
    "TEST_POSTGRES_URL" not in os.environ, reason="TEST_POSTGRES_URL not set"
)

CONFIG = {
    "category": "earbuds",
    "prompt_ids": ["p01", "p02"],
    "answer_providers": ["gemini", "openai"],
    "repeats": 2,
}


@pytest.fixture
def pg(monkeypatch: pytest.MonkeyPatch) -> Iterator[sessionmaker[Session]]:
    url = os.environ["TEST_POSTGRES_URL"]
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config(str(REPO_ROOT / "alembic.ini"))
    command.upgrade(config, "head")
    engine = make_engine(url)
    factory = make_session_factory(engine)
    try:
        with factory.begin() as session:
            seed_database(session, load_catalogue(DEMO_DIR), load_prompts(DEMO_DIR / PROMPTS_FILE))
        yield factory
    finally:
        engine.dispose()
        command.downgrade(config, "base")


def test_skip_locked_gives_two_workers_different_runs(pg: sessionmaker[Session]) -> None:
    first = create_run(pg, CONFIG, key="a")
    second = create_run(pg, CONFIG, key="b")

    # Worker A locks the oldest queued run and keeps its transaction open.
    worker_a = pg()
    worker_a.begin()
    locked = worker_a.scalars(queued_run_query()).first()
    try:
        assert locked.id == first
        # Worker B does not wait for A's lock: it skips that row and takes the next one.
        assert claim_next_run(pg) == second
    finally:
        worker_a.rollback()
        worker_a.close()

    # A's lock is gone, so the first run is still queued and can be claimed now.
    assert claim_next_run(pg) == first
    assert claim_next_run(pg) is None


def test_full_pipeline_on_postgres(pg: sessionmaker[Session]) -> None:
    run_id = create_run(pg, CONFIG)
    assert claim_next_run(pg) == run_id

    status = process_run(
        run_id,
        session_factory=pg,
        settings=make_settings(),
        answer_client_for=Writers(),
        verifier_client=FakeVerifier(),
        sleep=lambda _: None,
    )

    assert status == RunStatus.COMPLETED
    with pg() as session:
        run = session.get(db.AuditRun, run_id)
        assert run.metrics["answers"]["verified"] == 8
        assert run.metrics["claims"]["labels"]["contradicted"]["count"] == 4
        assert session.query(db.ReviewItem).count() == 4
