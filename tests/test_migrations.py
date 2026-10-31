"""The migration must apply, roll back fully, apply again, and match the models.

SQLite always runs. PostgreSQL runs only when TEST_POSTGRES_URL points at an empty
database, for example postgresql+psycopg://auditor:auditor@localhost:5432/auditor_test.
"""

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from .conftest import REPO_ROOT


def run_migration_cycle(monkeypatch: pytest.MonkeyPatch, database_url: str) -> None:
    # env.py reads DATABASE_URL through Settings.
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config(str(REPO_ROOT / "alembic.ini"))
    engine = create_engine(database_url)
    try:
        command.upgrade(config, "head")
        command.downgrade(config, "base")
        assert inspect(engine).get_table_names() == ["alembic_version"]

        command.upgrade(config, "head")
        # Fails if the models and the migrations disagree.
        command.check(config)
    finally:
        command.downgrade(config, "base")
        engine.dispose()


def test_migrations_on_sqlite(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    run_migration_cycle(monkeypatch, f"sqlite:///{(tmp_path / 'migrations.db').as_posix()}")


@pytest.mark.skipif("TEST_POSTGRES_URL" not in os.environ, reason="TEST_POSTGRES_URL not set")
def test_migrations_on_postgres(monkeypatch: pytest.MonkeyPatch) -> None:
    run_migration_cycle(monkeypatch, os.environ["TEST_POSTGRES_URL"])
