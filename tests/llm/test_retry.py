import pytest

from auditor.llm.errors import (
    PermanentProviderError,
    ProviderConfigError,
    ProviderTimeoutError,
    TransientProviderError,
)
from auditor.llm.retry import backoff_delay, call_with_retries


class Flaky:
    """Raises the given errors in order, then returns "ok"."""

    def __init__(self, *errors: Exception) -> None:
        self.errors = list(errors)
        self.calls = 0

    def __call__(self) -> str:
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
        return "ok"


def test_backoff_doubles_and_adds_up_to_half_a_second_of_jitter() -> None:
    assert [backoff_delay(n, rand=lambda: 0.0) for n in (1, 2, 3, 4)] == [1.0, 2.0, 4.0, 8.0]
    assert [backoff_delay(n, rand=lambda: 1.0) for n in (1, 2, 3)] == [1.5, 2.5, 4.5]


def test_transient_errors_are_retried_with_growing_delays() -> None:
    fn = Flaky(TransientProviderError("429"), ProviderTimeoutError("slow"))
    delays: list[float] = []

    result = call_with_retries(fn, max_retries=3, sleep=delays.append, rand=lambda: 0.0)

    assert result == "ok"
    assert fn.calls == 3
    assert delays == [1.0, 2.0]


def test_retries_are_bounded() -> None:
    fn = Flaky(*[TransientProviderError("503")] * 10)
    delays: list[float] = []

    with pytest.raises(TransientProviderError):
        call_with_retries(fn, max_retries=3, sleep=delays.append, rand=lambda: 0.0)

    assert fn.calls == 4  # the first attempt + 3 retries
    assert delays == [1.0, 2.0, 4.0]


@pytest.mark.parametrize("error", [PermanentProviderError("400"), ProviderConfigError("401")])
def test_non_transient_errors_are_not_retried(error: Exception) -> None:
    fn = Flaky(error)
    delays: list[float] = []

    with pytest.raises(type(error)):
        call_with_retries(fn, max_retries=3, sleep=delays.append)

    assert fn.calls == 1
    assert delays == []


def test_zero_retries_means_one_attempt() -> None:
    fn = Flaky(TransientProviderError("429"))
    with pytest.raises(TransientProviderError):
        call_with_retries(fn, max_retries=0, sleep=lambda _: None)
    assert fn.calls == 1
