"""The `auditor` command-line tool.

auditor seed            load the catalogue and prompt CSVs into the database
auditor create-api-key  create an API client and print its key once
auditor check-data      check the catalogue, prompts and eval set (no database needed)
auditor worker [--once] process queued audit runs
auditor eval            run the verifier over the eval set and write a report
auditor compare         compare two eval reports; fails on a regression
"""

import argparse
import json
import logging
from collections import Counter
from pathlib import Path

from auditor.api.security import create_api_client
from auditor.audit.worker import Worker
from auditor.catalogue.loader import (
    PROMPTS_FILE,
    CatalogueError,
    load_catalogue,
    load_prompts,
    seed_database,
)
from auditor.catalogue.repository import InMemoryCatalogue
from auditor.config import Settings
from auditor.db.models import utc_now
from auditor.db.session import make_engine, make_session_factory
from auditor.evals.dataset import DATASET_FILE, Dataset, DatasetError, load_dataset
from auditor.evals.runner import CompareRefused, compare_reports, report_markdown, run_eval
from auditor.llm.factory import build_verifier_client

DEFAULT_DATA_DIR = Path("data/demo")
DEFAULT_REPORTS_DIR = Path("reports")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="auditor")
    commands = parser.add_subparsers(dest="command", required=True)

    seed = commands.add_parser("seed", help="Load catalogue and prompt CSVs into the database.")
    seed.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)

    key = commands.add_parser("create-api-key", help="Create an API client; print its key once.")
    key.add_argument("name")

    check = commands.add_parser("check-data", help="Check the catalogue, prompts and eval set.")
    check.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)

    worker = commands.add_parser("worker", help="Process queued audit runs.")
    worker.add_argument("--once", action="store_true", help="Process one run (if any), then exit.")

    evaluate = commands.add_parser("eval", help="Run the verifier over the eval set.")
    evaluate.add_argument("--split", choices=["dev", "holdout"], default="dev")
    evaluate.add_argument("--repeats", type=int, default=3)
    evaluate.add_argument("--prompt-version", choices=["v1", "v2"], default="v1")
    evaluate.add_argument("--answer-id", action="append", dest="answer_ids")
    evaluate.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    evaluate.add_argument("--out-dir", type=Path, default=DEFAULT_REPORTS_DIR)

    compare = commands.add_parser("compare", help="Compare two eval reports (JSON).")
    compare.add_argument("baseline", type=Path)
    compare.add_argument("candidate", type=Path)
    compare.add_argument("--max-drop", type=float, default=0.02)

    args = parser.parse_args(argv)
    match args.command:
        case "seed":
            return seed_command(args.data_dir)
        case "create-api-key":
            return create_api_key_command(args.name)
        case "check-data":
            return check_data_command(args.data_dir)
        case "worker":
            return worker_command(args.once)
        case "eval":
            return eval_command(args)
        case _:
            return compare_command(args.baseline, args.candidate, args.max_drop)


def seed_command(data_dir: Path) -> int:
    catalogue = load_catalogue(data_dir)
    prompts = load_prompts(data_dir / PROMPTS_FILE)
    engine = make_engine(Settings().database_url)
    with make_session_factory(engine).begin() as session:
        inserted = seed_database(session, catalogue, prompts)
    print("Inserted:", ", ".join(f"{count} {kind}" for kind, count in inserted.items()))
    return 0


def create_api_key_command(name: str) -> int:
    engine = make_engine(Settings().database_url)
    with make_session_factory(engine).begin() as session:
        client, key = create_api_client(session, name)
        client_id = client.id
    print(f"Created client {name!r} ({client_id}).")
    print(f"API key (shown once, store it now): {key}")
    return 0


def check_data_command(data_dir: Path) -> int:
    try:
        dataset = _load_data(data_dir)[1]
    except (CatalogueError, DatasetError) as exc:
        print(f"PROBLEMS:\n{exc}")
        return 1
    splits = Counter(answer.split for answer in dataset.answers)
    labels = Counter(gold.label.value for answer in dataset.answers for gold in answer.gold)
    print(f"Catalogue, prompts and eval set {dataset.version} are consistent.")
    print("Answers:", ", ".join(f"{count} {split}" for split, count in sorted(splits.items())))
    print("Gold labels:", ", ".join(f"{count} {label}" for label, count in sorted(labels.items())))
    print(f"Dataset sha256: {dataset.sha256}")
    return 0


def worker_command(once: bool) -> int:
    settings = Settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(message)s")
    worker = Worker(make_session_factory(make_engine(settings.database_url)), settings)
    worker.check_config()  # fail now, not on the first run
    if once:
        run_id = worker.run_once()
        print(f"Processed run {run_id}." if run_id else "No queued run.")
        return 0
    worker.run_forever()
    return 0


def eval_command(args: argparse.Namespace) -> int:
    """Run a LIVE eval with the configured verifier. This calls a real model API."""
    settings = Settings()
    catalogue, dataset = _load_data(args.data_dir)
    report = run_eval(
        dataset=dataset,
        split=args.split,
        repeats=args.repeats,
        client_factory=lambda: build_verifier_client(settings),
        catalogue=catalogue,
        settings=settings,
        prompt_version=args.prompt_version,
        answer_ids=args.answer_ids,
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"eval-{args.split}-{args.prompt_version}-{utc_now():%Y%m%dT%H%M%SZ}"
    json_path = args.out_dir / f"{stem}.json"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    markdown_path = args.out_dir / f"{stem}.md"
    markdown_path.write_text(report_markdown(report), encoding="utf-8")
    print(f"Wrote {json_path} and {markdown_path}")
    return 0


def compare_command(baseline_path: Path, candidate_path: Path, max_drop: float) -> int:
    """Exit 0 if no regression, 1 on a regression, 2 if the reports cannot be compared."""
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    try:
        comparison = compare_reports(baseline, candidate, max_drop)
    except CompareRefused as exc:
        print(f"REFUSED: {exc}")
        return 2
    for name, delta in comparison.deltas.items():
        print(f"{name}: {'n/a' if delta is None else f'{delta:+.3f}'}")
    if not comparison.ok:
        for regression in comparison.regressions:
            print(f"REGRESSION: {regression}")
        return 1
    print("OK: no regression beyond the allowed drop.")
    return 0


def _load_data(data_dir: Path) -> tuple[InMemoryCatalogue, Dataset]:
    catalogue = InMemoryCatalogue(load_catalogue(data_dir))
    prompt_ids = {prompt.prompt_id for prompt in load_prompts(data_dir / PROMPTS_FILE)}
    return catalogue, load_dataset(data_dir / DATASET_FILE, catalogue, prompt_ids)
