"""The background worker: takes queued runs from the database and processes them."""

import logging
import signal
import time
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta

from auditor.audit.pipeline import (
    SessionFactory,
    claim_next_run,
    process_run,
    requeue_stale_runs,
)
from auditor.config import Settings
from auditor.db.models import utc_now
from auditor.enums import Provider
from auditor.llm.factory import build_verifier_client
from auditor.llm.types import LLMClient

logger = logging.getLogger(__name__)


class Worker:
    """Polls for queued runs. Several workers can run at once: SKIP LOCKED gives each a
    different run, and a crashed worker's run is requeued once its heartbeat is stale."""

    def __init__(
        self,
        session_factory: SessionFactory,
        settings: Settings,
        *,
        answer_client_for: Callable[[Provider], LLMClient] | None = None,
        verifier_client: LLMClient | None = None,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], datetime] = utc_now,
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings
        self._answer_client_for = answer_client_for
        self._verifier_client = verifier_client
        self._sleep = sleep
        self._now = now
        self._stopping = False

    def check_config(self) -> None:
        """Fail at startup if the verifier cannot be built (provider, model or key missing),
        instead of failing every run later. Raises ProviderConfigError."""
        if self._verifier_client is None:
            self._verifier_client = build_verifier_client(self._settings)

    def run_once(self) -> uuid.UUID | None:
        """Requeue stale runs, then process the next queued run. Returns its ID, or None."""
        requeued = requeue_stale_runs(
            self._session_factory, timedelta(seconds=self._settings.stale_run_seconds), self._now
        )
        if requeued:
            logger.warning("requeued %d stale run(s)", requeued)
        run_id = claim_next_run(self._session_factory, self._now)
        if run_id is None:
            return None
        status = process_run(
            run_id,
            session_factory=self._session_factory,
            settings=self._settings,
            answer_client_for=self._answer_client_for,
            verifier_client=self._verifier_client,
            sleep=self._sleep,
            now=self._now,
            should_stop=lambda: self._stopping,
        )
        logger.info("run %s finished: %s", run_id, status)
        return run_id

    def run_forever(self) -> None:
        """Process runs until SIGTERM or Ctrl+C.

        A stop signal does not kill the current run mid-answer: the run checks the flag
        before each model call, hands itself back to the queue, and the loop exits.
        """
        signal.signal(signal.SIGTERM, self._request_stop)
        signal.signal(signal.SIGINT, self._request_stop)
        logger.info("worker started")
        while not self._stopping:
            if self.run_once() is None and not self._stopping:
                self._sleep(self._settings.worker_poll_seconds)
        logger.info("worker stopped")

    def _request_stop(self, signum: int, _frame: object) -> None:
        logger.info("received signal %d; stopping after the current step", signum)
        self._stopping = True
