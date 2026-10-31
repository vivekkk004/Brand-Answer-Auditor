from collections import Counter

import pytest
from pydantic import ValidationError

from auditor.catalogue.loader import PROMPTS_FILE, load_prompts
from auditor.catalogue.repository import InMemoryCatalogue
from auditor.catalogue.schema import CatalogueData
from auditor.cli import EVAL_SET_FILE, main
from auditor.enums import ClaimLabel
from auditor.evalset import EvalAnswer, EvalSet, GoldClaim, check_eval_set, load_eval_set

from .conftest import DEMO_DIR


def demo_prompt_ids() -> set[str]:
    return {prompt.prompt_id for prompt in load_prompts(DEMO_DIR / PROMPTS_FILE)}


def test_demo_eval_set_is_consistent(demo_catalogue: CatalogueData) -> None:
    eval_set = load_eval_set(DEMO_DIR / EVAL_SET_FILE)

    problems = check_eval_set(eval_set, InMemoryCatalogue(demo_catalogue), demo_prompt_ids())

    assert problems == []
    assert Counter(answer.split for answer in eval_set.answers) == {"dev": 12, "holdout": 4}
    labels = {claim.label for answer in eval_set.answers for claim in answer.gold_claims}
    assert labels == set(ClaimLabel)


def test_check_reports_missing_quote_and_unknown_fact(demo_catalogue: CatalogueData) -> None:
    answer = EvalAnswer(
        answer_id="bad",
        split="dev",
        prompt_id="p01",
        market="IN",
        text="The Zentro Air 2 costs ₹7,999.",
        gold_claims=[
            GoldClaim(
                quote="costs ₹6,999",
                brand_id="zentro",
                label=ClaimLabel.SUPPORTED,
                fact_ids=["zentro-air2-price-in"],
            ),
            GoldClaim(
                quote="The Zentro Air 2 costs ₹7,999",
                brand_id="zentro",
                label=ClaimLabel.SUPPORTED,
                fact_ids=["no-such-fact"],
            ),
        ],
    )
    eval_set = EvalSet(version="test", answers=[answer])

    problems = check_eval_set(eval_set, InMemoryCatalogue(demo_catalogue), demo_prompt_ids())

    assert problems == [
        "bad claim 1: quote not found in answer text: 'costs ₹6,999'",
        "bad claim 2: unknown fact ID 'no-such-fact'",
    ]


def test_supported_gold_claim_must_cite_a_fact() -> None:
    with pytest.raises(ValidationError, match="must cite at least one fact ID"):
        GoldClaim(quote="x", brand_id="zentro", label=ClaimLabel.SUPPORTED, fact_ids=[])


def test_check_eval_command_passes_on_demo_data() -> None:
    assert main(["check-eval", "--data-dir", str(DEMO_DIR)]) == 0
