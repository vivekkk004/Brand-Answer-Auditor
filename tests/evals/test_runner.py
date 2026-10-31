import copy
import json
from pathlib import Path

import pytest

from auditor.catalogue.repository import InMemoryCatalogue
from auditor.cli import main
from auditor.evals.dataset import Dataset
from auditor.evals.runner import (
    NOT_REAL_BANNER,
    CompareRefused,
    compare_reports,
    report_markdown,
    run_eval,
)
from auditor.llm.fake import ScriptedClient

from ..audit.fakes import make_settings
from ..conftest import DEMO_DIR
from .conftest import OracleClient


def oracle_report(dataset: Dataset, catalogue: InMemoryCatalogue, **options) -> dict:
    brand_ids = [brand.brand_id for brand in catalogue.list_brands()]
    options.setdefault("split", "dev")
    options.setdefault("repeats", 2)
    return run_eval(
        dataset=dataset,
        client_factory=lambda: OracleClient(dataset, brand_ids),
        catalogue=catalogue,
        settings=make_settings(),
        sleep=lambda _: None,
        **options,
    )


def test_oracle_scores_perfectly_but_is_not_a_real_run(
    dataset: Dataset, catalogue: InMemoryCatalogue
) -> None:
    report = oracle_report(dataset, catalogue)

    assert report["is_real_run"] is False
    for spread in report["metrics"].values():
        assert spread == {"mean": 1.0, "min": 1.0, "max": 1.0}
    assert report["consistency"] == 1.0
    assert report["failure_rate"] == {"total": 0.0, "by_type": {}}
    assert report["problems"] == []
    assert report["dataset"]["sha256"] == dataset.sha256
    assert report["dataset"]["answer_ids"] == [a.answer_id for a in dataset.select("dev")]
    assert report["cost_usd"] is None  # no prices configured
    assert report_markdown(report).startswith(NOT_REAL_BANNER)


def test_failures_are_counted_scored_as_misses_and_listed(
    dataset: Dataset, catalogue: InMemoryCatalogue
) -> None:
    report = run_eval(
        dataset=dataset,
        split="holdout",
        repeats=1,
        client_factory=lambda: ScriptedClient([RuntimeError("boom")] * 4),
        catalogue=catalogue,
        settings=make_settings(),
    )

    assert report["failure_rate"] == {"total": 1.0, "by_type": {"code": 1.0}}
    assert report["metrics"]["extraction_recall"]["mean"] == 0.0
    assert report["metrics"]["extraction_precision"]["mean"] is None  # nothing predicted
    assert report["consistency"] is None  # one repeat
    assert {problem["error_type"] for problem in report["problems"]} == {"code"}


def make_real(report: dict) -> dict:
    """A hand-made copy marked real, to test compare_reports' rules. Not a result."""
    real = copy.deepcopy(report)
    real["is_real_run"] = True
    return real


def with_mean(report: dict, metric: str, value: float) -> dict:
    changed = copy.deepcopy(report)
    changed["metrics"][metric]["mean"] = value
    return changed


@pytest.fixture
def baseline(dataset: Dataset, catalogue: InMemoryCatalogue) -> dict:
    return make_real(oracle_report(dataset, catalogue, repeats=1))


def test_compare_refuses_fake_runs(
    dataset: Dataset, catalogue: InMemoryCatalogue, baseline
) -> None:
    fake = oracle_report(dataset, catalogue, repeats=1)
    with pytest.raises(CompareRefused, match="the candidate report is not a real run"):
        compare_reports(baseline, fake, max_drop=0.02)


@pytest.mark.parametrize(
    ("field", "value"),
    [("sha256", "0" * 64), ("split", "holdout"), ("answer_ids", ["e01"])],
)
def test_compare_refuses_different_datasets(baseline: dict, field: str, value) -> None:
    other = copy.deepcopy(baseline)
    other["dataset"][field] = value
    with pytest.raises(CompareRefused, match=f"different dataset {field}"):
        compare_reports(baseline, other, max_drop=0.02)


def test_compare_detects_a_regression(baseline: dict) -> None:
    worse = with_mean(baseline, "contradicted_recall", 0.9)

    comparison = compare_reports(baseline, worse, max_drop=0.05)

    assert not comparison.ok
    assert comparison.regressions == ["contradicted_recall dropped by 0.100 (allowed 0.050)"]
    assert comparison.deltas["contradicted_recall"] == pytest.approx(-0.1)


def test_compare_allows_a_drop_within_the_tolerance(baseline: dict) -> None:
    slightly_worse = with_mean(baseline, "joint_f1", 0.97)
    assert compare_reports(baseline, slightly_worse, max_drop=0.05).ok


def test_compare_cli_exit_codes(tmp_path: Path, baseline: dict) -> None:
    def write(name: str, report: dict) -> str:
        path = tmp_path / name
        path.write_text(json.dumps(report), encoding="utf-8")
        return str(path)

    base = write("base.json", baseline)
    assert main(["compare", base, write("same.json", baseline)]) == 0
    worse = with_mean(baseline, "joint_f1", 0.5)
    assert main(["compare", base, write("worse.json", worse)]) == 1
    fake = {**baseline, "is_real_run": False}
    assert main(["compare", base, write("fake.json", fake)]) == 2


def test_eval_cli_writes_a_flagged_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dataset: Dataset,
    catalogue: InMemoryCatalogue,
) -> None:
    # The CLI normally builds the real verifier; here it gets the oracle. No API is called.
    brand_ids = [brand.brand_id for brand in catalogue.list_brands()]
    monkeypatch.setattr(
        "auditor.cli.build_verifier_client", lambda _: OracleClient(dataset, brand_ids)
    )
    monkeypatch.setenv("DATABASE_URL", "sqlite://")

    exit_code = main(
        [
            "eval",
            "--split",
            "dev",
            "--repeats",
            "1",
            "--answer-id",
            "e01",
            "--out-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    (markdown_path,) = tmp_path.glob("*.md")
    assert markdown_path.read_text(encoding="utf-8").startswith(NOT_REAL_BANNER)
    (json_path,) = tmp_path.glob("*.json")
    assert json.loads(json_path.read_text(encoding="utf-8"))["is_real_run"] is False


def test_check_data_cli_passes_on_the_demo_data() -> None:
    assert main(["check-data", "--data-dir", str(DEMO_DIR)]) == 0


def test_worker_without_verifier_settings_exits_with_one_line(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite://")

    assert main(["worker", "--once"]) == 2
    output = capsys.readouterr().out
    assert output.splitlines() == ["config: no verifier provider given: set VERIFIER_PROVIDER"]
