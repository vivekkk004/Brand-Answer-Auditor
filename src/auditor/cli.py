"""The `auditor` command-line tool."""

import argparse
import logging
from collections import Counter
from pathlib import Path

from auditor.audit.worker import Worker
from auditor.catalogue.loader import PROMPTS_FILE, load_catalogue, load_prompts, seed_database
from auditor.catalogue.repository import InMemoryCatalogue
from auditor.config import Settings
from auditor.db.session import make_engine, make_session_factory
from auditor.evalset import check_eval_set, load_eval_set

DEFAULT_DATA_DIR = Path("data/demo")
EVAL_SET_FILE = "eval_set.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="auditor")
    commands = parser.add_subparsers(dest="command", required=True)

    seed = commands.add_parser("seed", help="Load catalogue and prompt CSVs into the database.")
    seed.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)

    check = commands.add_parser("check-eval", help="Check the eval set against the catalogue.")
    check.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)

    commands.add_parser("worker", help="Process queued audit runs until stopped.")

    args = parser.parse_args(argv)
    if args.command == "seed":
        return seed_command(args.data_dir)
    if args.command == "worker":
        return worker_command()
    return check_eval_command(args.data_dir)


def seed_command(data_dir: Path) -> int:
    catalogue = load_catalogue(data_dir)
    prompts = load_prompts(data_dir / PROMPTS_FILE)
    engine = make_engine(Settings().database_url)
    with make_session_factory(engine).begin() as session:
        inserted = seed_database(session, catalogue, prompts)
    print("Inserted:", ", ".join(f"{count} {kind}" for kind, count in inserted.items()))
    return 0


def check_eval_command(data_dir: Path) -> int:
    catalogue = InMemoryCatalogue(load_catalogue(data_dir))
    prompt_ids = {prompt.prompt_id for prompt in load_prompts(data_dir / PROMPTS_FILE)}
    eval_set = load_eval_set(data_dir / EVAL_SET_FILE)

    problems = check_eval_set(eval_set, catalogue, prompt_ids)
    if problems:
        for problem in problems:
            print("PROBLEM:", problem)
        print(f"{len(problems)} problem(s) found.")
        return 1

    splits = Counter(answer.split for answer in eval_set.answers)
    labels = Counter(claim.label for answer in eval_set.answers for claim in answer.gold_claims)
    print(f"Eval set {eval_set.version} is consistent.")
    print("Answers:", ", ".join(f"{count} {split}" for split, count in sorted(splits.items())))
    print("Gold labels:", ", ".join(f"{count} {label}" for label, count in sorted(labels.items())))
    return 0


def worker_command() -> int:
    settings = Settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(message)s")
    worker = Worker(make_session_factory(make_engine(settings.database_url)), settings)
    worker.check_config()  # fail now, not on the first run
    worker.run_forever()
    return 0
