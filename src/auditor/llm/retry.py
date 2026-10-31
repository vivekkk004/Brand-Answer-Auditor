"""Retries with exponential backoff and jitter, for transient provider errors only."""

import random
import time
from collections.abc import Callable

from auditor.llm.errors import TransientProviderError

BASE_DELAY_SECONDS = 1.0
MAX_JITTER_SECONDS = 0.5


def backoff_delay(retry_number: int, rand: Callable[[], float] = random.random) -> float:
    """Seconds to wait before retry number 1, 2, 3, ...: 1 s, 2 s, 4 s, ... plus 0-0.5 s.

    Doubling gives a struggling server more time each round. The random jitter spreads
    clients out so they do not all retry at the same moment.
    """
    return BASE_DELAY_SECONDS * 2 ** (retry_number - 1) + rand() * MAX_JITTER_SECONDS


def call_with_retries[T](
    fn: Callable[[], T],
    *,
    max_retries: int,
    sleep: Callable[[float], None] = time.sleep,
    rand: Callable[[], float] = random.random,
) -> T:
    """Call `fn`; on a TransientProviderError, wait and try again, up to `max_retries` times.

    Any other error is raised at once: retrying a 400 or a bad API key gives the same
    answer. After the last retry the transient error is raised to the caller.
    `sleep` and `rand` are parameters so tests run instantly and predictably.
    """
    retries_done = 0
    while True:
        try:
            return fn()
        except TransientProviderError:
            if retries_done >= max_retries:
                raise
            retries_done += 1
            sleep(backoff_delay(retries_done, rand))
