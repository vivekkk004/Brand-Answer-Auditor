import pytest

from auditor.enums import ClaimLabel
from auditor.evals.dataset import GoldSpan
from auditor.evals.scoring import PredictedClaim, score_answer, summarise

S, C, U = ClaimLabel.SUPPORTED, ClaimLabel.CONTRADICTED, ClaimLabel.UNKNOWN


def gold(start: int, end: int, label: ClaimLabel) -> GoldSpan:
    return GoldSpan(start, end, f"q{start}", "zentro", label, ())


def predicted(start: int, end: int, label: ClaimLabel) -> PredictedClaim:
    return PredictedClaim(start, end, label, f"q{start}")


# Answer 1: four gold claims, two of them contradicted.
GOLD_1 = [gold(0, 10, S), gold(20, 30, C), gold(40, 50, C), gold(60, 70, U)]
PREDICTED_1 = [
    predicted(0, 10, S),  # exact span, right label
    predicted(20, 30, S),  # exact span, WRONG label (missed a contradiction)
    predicted(40, 49, C),  # off by one character: not a match
    predicted(80, 90, U),  # no gold claim here
]
# Answer 2: verification failed, so it predicts nothing.
GOLD_2 = [gold(0, 5, C)]


def test_scoring_one_answer() -> None:
    score = score_answer("a1", GOLD_1, PREDICTED_1)

    assert (score.gold_count, score.predicted_count) == (4, 4)
    assert (score.span_matches, score.joint_matches) == (2, 1)
    assert (score.contradicted_gold, score.contradicted_found) == (2, 0)
    assert [g.start for g in score.missed] == [40, 60]
    assert score.wrong_label == ((GOLD_1[1], S),)
    assert [p.start for p in score.unmatched] == [40, 80]


def test_a_failed_answer_predicts_nothing() -> None:
    score = score_answer("a2", GOLD_2, None)
    assert score.failed
    assert (score.predicted_count, score.span_matches) == (0, 0)
    assert score.missed == tuple(GOLD_2)


def test_summary_maths_by_hand() -> None:
    metrics = summarise([score_answer("a1", GOLD_1, PREDICTED_1), score_answer("a2", GOLD_2, None)])

    # Totals: gold 4 + 1 = 5, predicted 4 + 0 = 4, span matches 2, joint matches 1.
    # Extraction: P = 2/4, R = 2/5, F1 = 2PR/(P+R) = 0.4/0.9.
    assert metrics["extraction_precision"] == pytest.approx(0.5)
    assert metrics["extraction_recall"] == pytest.approx(0.4)
    assert metrics["extraction_f1"] == pytest.approx(0.4 / 0.9)
    # Joint: P = 1/4, R = 1/5, F1 = 2 * 0.25 * 0.2 / 0.45 = 0.1 / 0.45.
    assert metrics["joint_precision"] == pytest.approx(0.25)
    assert metrics["joint_recall"] == pytest.approx(0.2)
    assert metrics["joint_f1"] == pytest.approx(0.1 / 0.45)
    # Contradicted: 3 in gold (2 + 1), none found with the exact span and label.
    assert metrics["contradicted_recall"] == 0.0


def test_no_gold_and_no_predictions_gives_none_not_zero() -> None:
    metrics = summarise([score_answer("a", [], [])])
    assert metrics["extraction_precision"] is None
    assert metrics["extraction_recall"] is None
    assert metrics["contradicted_recall"] is None
