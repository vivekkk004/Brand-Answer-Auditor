from decimal import Decimal

import pytest

from auditor.metrics import estimate_cost_usd, percentile, precision_recall_f1, wilson_interval


@pytest.mark.parametrize(
    ("k", "n", "low", "high"),
    [
        # Standard reference values for the 95% Wilson interval (z = 1.959964).
        (0, 10, 0.0, 0.27753),
        (10, 10, 0.72247, 1.0),
        (5, 10, 0.23659, 0.76341),
        (1, 1, 0.20654, 1.0),
    ],
)
def test_wilson_interval(k: int, n: int, low: float, high: float) -> None:
    interval = wilson_interval(k, n)
    assert interval == pytest.approx((low, high), abs=1e-5)


def test_wilson_interval_with_no_data_is_none() -> None:
    assert wilson_interval(0, 0) is None


def test_wilson_interval_rejects_impossible_counts() -> None:
    with pytest.raises(ValueError):
        wilson_interval(3, 2)


def test_precision_recall_f1() -> None:
    assert precision_recall_f1(3, 4, 6) == pytest.approx((0.75, 0.5, 0.6))
    assert precision_recall_f1(0, 2, 2) == (0.0, 0.0, 0.0)
    assert precision_recall_f1(0, 0, 5) == (None, 0.0, None)
    assert precision_recall_f1(0, 3, 0) == (0.0, None, None)


def test_percentile_is_nearest_rank() -> None:
    values = list(range(1, 21))
    assert percentile(values, 50) == 10
    assert percentile(values, 95) == 19
    assert percentile(values, 100) == 20
    assert percentile([7.5], 95) == 7.5
    assert percentile([], 50) is None


def test_cost_needs_prices_and_token_counts() -> None:
    cost = estimate_cost_usd(1_000_000, 500_000, Decimal("1"), Decimal("4"))
    assert cost == Decimal("3")
    assert estimate_cost_usd(100, 100, None, Decimal("4")) is None
    assert estimate_cost_usd(None, 100, Decimal("1"), Decimal("4")) is None
