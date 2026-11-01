"""Running the verifier over the eval set, writing a report, and comparing two reports.

Honesty rules built into the report:
- Every number is computed here from model outputs and the gold set; nothing is typed in.
- `is_real_run` is decided from the client's type, not passed in by the caller, so a
  fake client can never produce a report that claims to be real.
- A fake run's Markdown starts with "NOT A REAL RESULT", and compare_reports refuses it.
- The report records the dataset fingerprint, split, git commit, model and settings, so
  any number can be traced to exactly what produced it.
"""

import subprocess
import time
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from auditor.agent.verifier import verify_answer
from auditor.catalogue.repository import Catalogue
from auditor.config import Settings
from auditor.db.models import utc_now
from auditor.evals.dataset import Dataset
from auditor.evals.scoring import AnswerScore, PredictedClaim, score_answer, summarise
from auditor.llm.gemini_client import GeminiClient
from auditor.llm.groq_client import GroqClient
from auditor.llm.openai_client import OpenAIClient
from auditor.llm.types import LLMClient
from auditor.metrics import estimate_cost_usd, percentile

METRICS = (
    "extraction_precision",
    "extraction_recall",
    "extraction_f1",
    "joint_precision",
    "joint_recall",
    "joint_f1",
    "contradicted_recall",
)
# The two numbers a change must not make worse (compare_reports).
GUARDED_METRICS = ("joint_f1", "contradicted_recall")
NOT_REAL_BANNER = (
    "NOT A REAL RESULT: this report was produced by a fake model client. "
    "Its numbers say nothing about any real model and must not be quoted."
)
REPO_ROOT = Path(__file__).resolve().parents[3]


def run_eval(
    *,
    dataset: Dataset,
    split: str,
    repeats: int,
    client_factory: Callable[[], LLMClient],
    catalogue: Catalogue,
    settings: Settings,
    prompt_version: str = "v1",
    answer_ids: list[str] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], datetime] = utc_now,
) -> dict[str, Any]:
    """Verify every answer of `split`, `repeats` times, and build the report.

    Repeats matter because the model is not deterministic: one run could be lucky.
    Each metric is reported as mean, min and max over the repeats.
    """
    if repeats < 1:
        raise ValueError("repeats must be at least 1")
    answers = dataset.select(split, answer_ids)
    client = client_factory()

    per_repeat: list[dict[str, float | None]] = []
    outputs: dict[str, list[frozenset | None]] = {a.answer_id: [] for a in answers}
    failures: Counter[str] = Counter()
    latencies: list[float] = []
    tokens = {"input": None, "output": None, "thinking": None}
    problems: list[dict[str, Any]] = []

    for repeat in range(1, repeats + 1):
        scores: list[AnswerScore] = []
        for answer in answers:
            # A config error (missing key, rejected credentials) is raised: it would fail
            # every answer the same way, so the eval stops instead of scoring failures.
            result = verify_answer(
                answer_text=answer.text,
                client=client,
                catalogue=catalogue,
                market=answer.market,
                prompt_version=prompt_version,
                max_turns=settings.agent_max_turns,
                max_retries=settings.llm_max_retries,
                sleep=sleep,
            )
            latencies.append(result.latency_ms)
            for key, value in (
                ("input", result.tokens.input_tokens),
                ("output", result.tokens.output_tokens),
                ("thinking", result.tokens.thinking_tokens),
            ):
                if value is not None:
                    tokens[key] = (tokens[key] or 0) + value

            if result.ok:
                predicted = [
                    PredictedClaim(c.start, c.end, c.label, c.quote) for c in result.claims
                ]
                outputs[answer.answer_id].append(
                    frozenset((p.start, p.end, p.label) for p in predicted)
                )
            else:
                predicted = None
                failures[result.error_type.value] += 1
                outputs[answer.answer_id].append(None)

            score = score_answer(answer.answer_id, answer.gold, predicted)
            scores.append(score)
            if score.failed or score.missed or score.wrong_label or score.unmatched:
                problems.append(_problem_entry(repeat, score, result.error_type))
        per_repeat.append(summarise(scores))

    attempts = len(answers) * repeats
    cost = estimate_cost_usd(
        tokens["input"],
        tokens["output"],
        settings.input_token_price_per_million,
        settings.output_token_price_per_million,
    )
    return {
        "is_real_run": isinstance(client, GeminiClient | OpenAIClient | GroqClient),
        "created_at": now().isoformat(),
        "git": _git_info(),
        "dataset": {
            "version": dataset.version,
            "sha256": dataset.sha256,
            "split": split,
            "answer_ids": [answer.answer_id for answer in answers],
        },
        "settings": {
            "provider": str(settings.verifier_provider) if settings.verifier_provider else None,
            "model": client.model,
            "prompt_version": prompt_version,
            "temperature": settings.llm_temperature,
            "max_turns": settings.agent_max_turns,
            "max_retries": settings.llm_max_retries,
        },
        "repeats": repeats,
        "metrics": {name: _spread([m[name] for m in per_repeat]) for name in METRICS},
        "failure_rate": {
            "total": sum(failures.values()) / attempts if attempts else None,
            "by_type": {k: v / attempts for k, v in sorted(failures.items())},
        },
        "consistency": _consistency(outputs, repeats),
        "latency_ms": {"p50": percentile(latencies, 50), "p95": percentile(latencies, 95)},
        "tokens": {
            **tokens,
            "per_answer_mean": {
                key: value / attempts if value is not None and attempts else None
                for key, value in tokens.items()
            },
        },
        "cost_usd": float(cost) if cost is not None else None,
        "problems": problems,
    }


def _spread(values: Sequence[float | None]) -> dict[str, float | None]:
    """Mean, min and max over repeats, ignoring repeats where the metric had no data."""
    present = [value for value in values if value is not None]
    if not present:
        return {"mean": None, "min": None, "max": None}
    return {"mean": sum(present) / len(present), "min": min(present), "max": max(present)}


def _consistency(outputs: dict[str, list[frozenset | None]], repeats: int) -> float | None:
    """Share of answers that got exactly the same claims (spans and labels) in every
    repeat. A failed repeat is its own outcome. Meaningless with one repeat, so None."""
    if repeats < 2 or not outputs:
        return None
    same = sum(len(set(results)) == 1 for results in outputs.values())
    return same / len(outputs)


def _problem_entry(repeat: int, score: AnswerScore, error_type) -> dict[str, Any]:
    return {
        "repeat": repeat,
        "answer_id": score.answer_id,
        "failed": score.failed,
        "error_type": error_type.value if score.failed and error_type else None,
        "missed": [{"quote": g.quote, "label": g.label.value} for g in score.missed],
        "wrong_label": [
            {"quote": g.quote, "gold": g.label.value, "predicted": label.value}
            for g, label in score.wrong_label
        ],
        "unmatched": [{"quote": p.quote, "label": p.label.value} for p in score.unmatched],
    }


def _git_info() -> dict[str, Any]:
    """The commit the code ran at, and whether there were uncommitted changes."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}
    return {"commit": commit, "dirty": bool(dirty)}


def report_markdown(report: dict[str, Any]) -> str:
    lines = []
    if not report["is_real_run"]:
        lines += [NOT_REAL_BANNER, ""]
    settings, dataset = report["settings"], report["dataset"]
    lines += [
        "# Verifier eval report",
        "",
        f"- Model: {settings['provider']} / {settings['model']}, "
        f"prompt {settings['prompt_version']}",
        f"- Dataset: {dataset['version']} (sha256 {dataset['sha256'][:12]}), split "
        f"{dataset['split']}, {len(dataset['answer_ids'])} answers x {report['repeats']} repeats",
        f"- Code: commit {report['git']['commit']}, uncommitted changes: {report['git']['dirty']}",
        f"- Created: {report['created_at']}",
        "",
        "| metric | mean | min | max |",
        "|--------|------|-----|-----|",
    ]
    for name, spread in report["metrics"].items():
        lines.append(
            f"| {name} | {_fmt(spread['mean'])} | {_fmt(spread['min'])} | {_fmt(spread['max'])} |"
        )
    lines += [
        "",
        f"- Failure rate: {_fmt(report['failure_rate']['total'])} "
        f"{report['failure_rate']['by_type'] or ''}".rstrip(),
        f"- Consistency across repeats: {_fmt(report['consistency'])}",
        f"- Latency p50 / p95 (ms): {_fmt(report['latency_ms']['p50'])} / "
        f"{_fmt(report['latency_ms']['p95'])}",
        f"- Tokens in / out: {report['tokens']['input']} / {report['tokens']['output']}",
        f"- Cost (USD): {_fmt(report['cost_usd'])}",
        f"- Answers with problems (all repeats): {len(report['problems'])}",
    ]
    return "\n".join(lines) + "\n"


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


# --- Comparing two reports ---


class CompareRefused(ValueError):
    """The two reports cannot be compared fairly."""


@dataclass(frozen=True)
class Comparison:
    ok: bool
    regressions: list[str]
    deltas: dict[str, float | None]


def compare_reports(
    baseline: dict[str, Any], candidate: dict[str, Any], max_drop: float
) -> Comparison:
    """Check that `candidate` is not worse than `baseline` on the guarded metrics.

    Refused (CompareRefused) when the comparison would be meaningless: a fake run on
    either side, or a different dataset, split or set of answers. Fails (ok=False) when
    joint F1 or contradicted recall drops by more than `max_drop`.
    """
    if not 0 <= max_drop <= 1:
        raise ValueError("max_drop must be between 0 and 1")
    reasons = []
    for name, report in (("baseline", baseline), ("candidate", candidate)):
        if not report.get("is_real_run"):
            reasons.append(f"the {name} report is not a real run")
    for field in ("sha256", "split", "answer_ids"):
        if baseline["dataset"][field] != candidate["dataset"][field]:
            reasons.append(f"the reports use a different dataset {field}")
    if reasons:
        raise CompareRefused("; ".join(reasons))

    deltas: dict[str, float | None] = {}
    for name in METRICS:
        before = baseline["metrics"][name]["mean"]
        after = candidate["metrics"][name]["mean"]
        deltas[name] = None if before is None or after is None else after - before

    regressions = []
    for name in GUARDED_METRICS:
        if deltas[name] is None:
            regressions.append(f"{name}: missing in one of the reports")
        elif deltas[name] < -max_drop:
            regressions.append(f"{name} dropped by {-deltas[name]:.3f} (allowed {max_drop:.3f})")
    return Comparison(ok=not regressions, regressions=regressions, deltas=deltas)
