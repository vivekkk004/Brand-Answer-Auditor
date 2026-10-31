import signal
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session, sessionmaker

from auditor.audit.pipeline import claim_next_run, requeue_stale_runs
from auditor.audit.worker import Worker
from auditor.db import models as db
from auditor.enums import RunStatus
from auditor.llm.errors import ProviderConfigError
from auditor.llm.gemini_client import GeminiClient

from .fakes import FakeVerifier, Writers, create_run, make_settings

Factory = sessionmaker[Session]
NOW = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
CONFIG = {
    "category": "earbuds",
    "prompt_ids": ["p01"],
    "answer_providers": ["gemini"],
    "repeats": 1,
}


def make_worker(factory: Factory, **options) -> Worker:
    options.setdefault("answer_client_for", Writers())
    options.setdefault("verifier_client", FakeVerifier())
    return Worker(factory, make_settings(), sleep=lambda _: None, now=lambda: NOW, **options)


def status_of(factory: Factory, run_id) -> RunStatus:
    with factory() as session:
        return session.get(db.AuditRun, run_id).status


def set_running(factory: Factory, run_id, heartbeat: datetime) -> None:
    with factory.begin() as session:
        run = session.get(db.AuditRun, run_id)
        run.status = RunStatus.RUNNING
        run.heartbeat_at = heartbeat


def test_claim_takes_the_oldest_queued_run(seeded: Factory) -> None:
    first = create_run(seeded, CONFIG, key="a")
    second = create_run(seeded, CONFIG, key="b")

    assert claim_next_run(seeded) == first
    assert claim_next_run(seeded) == second
    assert claim_next_run(seeded) is None
    assert status_of(seeded, first) == RunStatus.RUNNING


def test_run_once_processes_one_queued_run(seeded: Factory) -> None:
    run_id = create_run(seeded, CONFIG)
    worker = make_worker(seeded)

    assert worker.run_once() == run_id
    assert status_of(seeded, run_id) == RunStatus.COMPLETED
    assert worker.run_once() is None


def test_stale_runs_are_requeued(seeded: Factory) -> None:
    stale = create_run(seeded, CONFIG, key="stale")
    alive = create_run(seeded, CONFIG, key="alive")
    set_running(seeded, stale, heartbeat=NOW - timedelta(minutes=20))
    set_running(seeded, alive, heartbeat=NOW - timedelta(minutes=1))

    assert requeue_stale_runs(seeded, timedelta(minutes=15), now=lambda: NOW) == 1
    assert status_of(seeded, stale) == RunStatus.QUEUED
    assert status_of(seeded, alive) == RunStatus.RUNNING


def test_run_once_picks_up_a_stale_run(seeded: Factory) -> None:
    run_id = create_run(seeded, CONFIG)
    set_running(seeded, run_id, heartbeat=NOW - timedelta(hours=1))

    assert make_worker(seeded).run_once() == run_id
    assert status_of(seeded, run_id) == RunStatus.COMPLETED


def test_check_config_fails_at_startup_without_a_verifier(seeded: Factory) -> None:
    worker = Worker(seeded, make_settings(verifier_provider=None))
    with pytest.raises(ProviderConfigError, match="VERIFIER_PROVIDER"):
        worker.check_config()


def test_check_config_builds_the_verifier(seeded: Factory) -> None:
    worker = Worker(seeded, make_settings())
    worker.check_config()
    assert isinstance(worker._verifier_client, GeminiClient)


def test_run_forever_stops_on_sigterm(seeded: Factory) -> None:
    worker = make_worker(seeded)
    # The fake sleep "receives" SIGTERM while the worker waits for work.
    worker._sleep = lambda _: worker._request_stop(signal.SIGTERM, None)
    original = signal.getsignal(signal.SIGTERM), signal.getsignal(signal.SIGINT)
    try:
        worker.run_forever()
    finally:
        signal.signal(signal.SIGTERM, original[0])
        signal.signal(signal.SIGINT, original[1])
    assert worker._stopping is True
