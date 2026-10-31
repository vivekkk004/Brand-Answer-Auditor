"""Pure metric functions. Every metric in reports is computed with these, from stored rows.

A metric whose denominator is 0 returns None, never 0 or 1: "no data" is not "0%".
"""

import math
from collections.abc import Sequence
from decimal import Decimal

Z_95 = 1.959964


def wilson_interval(k: int, n: int, z: float = Z_95) -> tuple[float, float] | None:
    """95% Wilson score interval for k successes out of n (SPEC 7.1).

    Chosen over the simple p ± z*sqrt(p(1-p)/n) because that one gives [0, 0] for
    0 out of 10 (false certainty) and can leave [0, 1]. Wilson stays honest at small n.
    """
    if not 0 <= k <= n:
        raise ValueError(f"need 0 <= k <= n, got k={k}, n={n}")
    if n == 0:
        return None
    p = k / n
    denominator = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denominator
    half_width = (z / denominator) * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    # max/min only remove floating-point dust such as -1e-17.
    return max(0.0, centre - half_width), min(1.0, centre + half_width)


def precision_recall_f1(
    true_positives: int, predicted: int, gold: int
) -> tuple[float | None, float | None, float | None]:
    """Precision = TP / predicted, recall = TP / gold, F1 = their harmonic mean."""
    precision = true_positives / predicted if predicted else None
    recall = true_positives / gold if gold else None
    if precision is None or recall is None:
        return precision, recall, None
    if precision + recall == 0:
        return precision, recall, 0.0
    return precision, recall, 2 * precision * recall / (precision + recall)


def percentile(values: Sequence[float], q: float) -> float | None:
    """Nearest-rank percentile (q in 0-100): always an actually observed value.

    p95 of 20 latencies is the 19th smallest. No interpolation, so it is easy to check
    by hand.
    """
    if not 0 <= q <= 100:
        raise ValueError(f"q must be between 0 and 100, got {q}")
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(q / 100 * len(ordered)))
    return ordered[rank - 1]


def estimate_cost_usd(
    input_tokens: int | None,
    output_tokens: int | None,
    input_price_per_million: Decimal | None,
    output_price_per_million: Decimal | None,
) -> Decimal | None:
    """Cost from reported tokens and configured prices, or None.

    None whenever a price or a token count is missing: we never guess a price or a
    token count, so a cost is either computed from real inputs or not shown at all.
    """
    if None in (input_tokens, output_tokens, input_price_per_million, output_price_per_million):
        return None
    million = Decimal(1_000_000)
    return (
        Decimal(input_tokens) * input_price_per_million / million
        + Decimal(output_tokens) * output_price_per_million / million
    )
