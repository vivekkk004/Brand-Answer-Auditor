import json
from collections import Counter
from pathlib import Path

import pytest

from auditor.catalogue.repository import InMemoryCatalogue
from auditor.enums import ClaimLabel
from auditor.evals.dataset import Dataset, DatasetError, fingerprint, load_dataset

from ..conftest import DEMO_DIR

DATASET = DEMO_DIR / "eval_set.json"


def test_dataset_counts(dataset: Dataset) -> None:
    assert dataset.version == "demo-v1"
    assert Counter(answer.split for answer in dataset.answers) == {"dev": 12, "holdout": 4}
    labels = {gold.label for answer in dataset.answers for gold in answer.gold}
    assert labels == set(ClaimLabel)
    assert len(dataset.select("dev")) == 12
    assert len(dataset.select("holdout")) == 4


def test_gold_offsets_point_at_the_quotes(dataset: Dataset) -> None:
    for answer in dataset.answers:
        for gold in answer.gold:
            assert answer.text[gold.start : gold.end] == gold.quote


def test_fingerprint_ignores_formatting_but_not_content() -> None:
    raw = json.loads(DATASET.read_text(encoding="utf-8"))
    assert len(fingerprint(raw)) == 64
    reformatted = json.loads(json.dumps(raw, indent=4))
    assert fingerprint(reformatted) == fingerprint(raw)

    raw["answers"][0]["gold_claims"][0]["label"] = "unknown"
    assert fingerprint(raw) != fingerprint(reformatted)


def test_select_rejects_unknown_answer_ids_and_splits(dataset: Dataset) -> None:
    assert [a.answer_id for a in dataset.select("dev", ["e02", "e01"])] == ["e02", "e01"]
    with pytest.raises(DatasetError, match="unknown answer IDs in split 'dev': \\['e13'\\]"):
        dataset.select("dev", ["e01", "e13"])  # e13 is a holdout answer
    with pytest.raises(DatasetError, match="unknown split"):
        dataset.select("train")


def write_dataset(tmp_path: Path, answers: list[dict]) -> Path:
    path = tmp_path / "eval_set.json"
    path.write_text(json.dumps({"version": "test", "answers": answers}), encoding="utf-8")
    return path


def answer(text: str, *claims: dict, answer_id: str = "a1", prompt_id: str = "p01") -> dict:
    return {
        "answer_id": answer_id,
        "split": "dev",
        "prompt_id": prompt_id,
        "market": "IN",
        "text": text,
        "gold_claims": list(claims),
    }


def claim(quote: str, label: str = "supported", fact_ids=("zentro-air2-ipx",)) -> dict:
    return {"quote": quote, "brand_id": "zentro", "label": label, "fact_ids": list(fact_ids)}


def test_a_repeated_sentence_gets_offsets_like_the_validator(
    tmp_path: Path, catalogue: InMemoryCatalogue, prompt_ids: set[str]
) -> None:
    text = "It is rated IPX4. It is rated IPX4."
    path = write_dataset(
        tmp_path, [answer(text, claim("It is rated IPX4"), claim("It is rated IPX4"))]
    )

    gold = load_dataset(path, catalogue, prompt_ids).answers[0].gold

    assert [(g.start, g.end) for g in gold] == [(0, 16), (18, 34)]


def test_broken_gold_file_is_rejected_with_every_problem(
    tmp_path: Path, catalogue: InMemoryCatalogue, prompt_ids: set[str]
) -> None:
    path = write_dataset(
        tmp_path,
        [
            answer(
                "The Zentro Air 2 is rated IPX4.",
                claim("is rated IPX7"),
                claim("is rated IPX4", fact_ids=["no-such-fact"]),
            ),
            answer("Another answer.", answer_id="a1", prompt_id="p99"),
        ],
    )

    with pytest.raises(DatasetError) as error:
        load_dataset(path, catalogue, prompt_ids)

    assert error.value.problems == [
        "a1 claim 1: quote not found in the answer text (or every occurrence is already used "
        "by an earlier gold claim): 'is rated IPX7'",
        "a1 claim 2: unknown fact ID 'no-such-fact'",
        "a1: duplicate answer_id",
        "a1: unknown prompt_id 'p99'",
    ]


@pytest.mark.parametrize(
    ("bad_claim", "message"),
    [
        (claim("is rated", label="mostly-true"), "label"),
        (claim("is rated", fact_ids=[]), "must cite at least one fact ID"),
        ({**claim("is rated"), "surprise": 1}, "Extra inputs are not permitted"),
    ],
)
def test_bad_labels_and_fields_are_rejected(
    tmp_path: Path, catalogue: InMemoryCatalogue, prompt_ids: set[str], bad_claim, message
) -> None:
    path = write_dataset(tmp_path, [answer("It is rated IPX4.", bad_claim)])
    with pytest.raises(DatasetError, match=message):
        load_dataset(path, catalogue, prompt_ids)


def test_invalid_json_is_rejected(
    tmp_path: Path, catalogue: InMemoryCatalogue, prompt_ids: set[str]
) -> None:
    path = tmp_path / "eval_set.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(DatasetError, match="invalid JSON"):
        load_dataset(path, catalogue, prompt_ids)
