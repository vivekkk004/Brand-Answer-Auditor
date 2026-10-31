"""Scoring predicted claims against gold claims (SPEC 7.3).

Matching is by EXACT span: a prediction matches a gold claim only if both its start and
its end are equal. Partial overlaps do not count. That is strict, but it is simple to
explain and impossible to game, and the agent's offsets come from code, not the model.

Totals are summed over all answers before dividing (micro-average), so an answer with
many claims counts for more than an answer with one.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from auditor.enums import ClaimLabel
from auditor.evals.dataset import GoldSpan
from auditor.metrics import precision_recall_f1


@dataclass(frozen=True)
class PredictedClaim:
    start: int
    end: int
    label: ClaimLabel
    quote: str


@dataclass(frozen=True)
class AnswerScore:
    answer_id: str
    failed: bool
    gold_count: int
    predicted_count: int
    span_matches: int
    joint_matches: int
    contradicted_gold: int
    contradicted_found: int
    # For error analysis: what went wrong, claim by claim.
    missed: tuple[GoldSpan, ...]
    wrong_label: tuple[tuple[GoldSpan, ClaimLabel], ...]
    unmatched: tuple[PredictedClaim, ...]


def score_answer(
    answer_id: str, gold: Sequence[GoldSpan], predicted: Sequence[PredictedClaim] | None
) -> AnswerScore:
    """Score one answer. `predicted=None` means verification failed: a failed answer
    predicts nothing, so every gold claim counts as missed (failures are not hidden)."""
    failed = predicted is None
    predicted = predicted or []
    gold_by_span = {(g.start, g.end): g for g in gold}
    predicted_spans = {(p.start, p.end) for p in predicted}

    span_matches = 0
    joint_matches = 0
    wrong_label = []
    unmatched = []
    for prediction in predicted:
        match = gold_by_span.get((prediction.start, prediction.end))
        if match is None:
            unmatched.append(prediction)
            continue
        span_matches += 1
        if prediction.label == match.label:
            joint_matches += 1
        else:
            wrong_label.append((match, prediction.label))

    predicted_labels = {(p.start, p.end): p.label for p in predicted}
    contradicted = [g for g in gold if g.label == ClaimLabel.CONTRADICTED]
    contradicted_found = sum(
        predicted_labels.get((g.start, g.end)) == ClaimLabel.CONTRADICTED for g in contradicted
    )
    return AnswerScore(
        answer_id=answer_id,
        failed=failed,
        gold_count=len(gold),
        predicted_count=len(predicted),
        span_matches=span_matches,
        joint_matches=joint_matches,
        contradicted_gold=len(contradicted),
        contradicted_found=contradicted_found,
        missed=tuple(g for g in gold if (g.start, g.end) not in predicted_spans),
        wrong_label=tuple(wrong_label),
        unmatched=tuple(unmatched),
    )


def summarise(scores: Sequence[AnswerScore]) -> dict[str, float | None]:
    """Extraction P/R/F1 (span only), joint P/R/F1 (span and label), and recall on
    contradicted claims, the number that matters most: a missed contradiction never
    reaches a human reviewer."""
    gold = sum(s.gold_count for s in scores)
    predicted = sum(s.predicted_count for s in scores)
    extraction = precision_recall_f1(sum(s.span_matches for s in scores), predicted, gold)
    joint = precision_recall_f1(sum(s.joint_matches for s in scores), predicted, gold)
    contradicted_gold = sum(s.contradicted_gold for s in scores)
    return {
        "extraction_precision": extraction[0],
        "extraction_recall": extraction[1],
        "extraction_f1": extraction[2],
        "joint_precision": joint[0],
        "joint_recall": joint[1],
        "joint_f1": joint[2],
        "contradicted_recall": (
            sum(s.contradicted_found for s in scores) / contradicted_gold
            if contradicted_gold
            else None
        ),
    }
