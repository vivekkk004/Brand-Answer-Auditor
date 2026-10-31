import pytest
from pydantic import ValidationError

from auditor.audit.mentions import MentionDetector
from auditor.audit.run_config import RunConfig
from auditor.catalogue.schema import Brand

BRANDS = [
    Brand(brand_id="zentro", name="Zentro", aliases=("Zentro Audio",)),
    Brand(brand_id="nova", name="Nova"),
    # One brand's name starts with another brand's name.
    Brand(brand_id="nova-sound", name="Nova Sound"),
]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("I like the Zentro Air 2.", ["zentro"]),
        ("ZENTRO and zentro audio", ["zentro"]),
        ("Zentrofy is not a brand.", []),
        ("The Nova Sound buds are fine.", ["nova-sound"]),
        ("Nova, or Nova Sound?", ["nova", "nova-sound"]),
        ("No brands here.", []),
    ],
)
def test_mentions_are_whole_word_case_insensitive_longest_first(
    text: str, expected: list[str]
) -> None:
    assert MentionDetector(BRANDS).detect(text) == expected


def test_no_brands_means_no_mentions() -> None:
    assert MentionDetector([]).detect("Zentro") == []


def test_run_config_defaults() -> None:
    config = RunConfig(category="earbuds", answer_providers=["gemini"])
    assert config.repeats == 3
    assert config.agent_version == "v1"
    assert config.prompt_ids is None


@pytest.mark.parametrize(
    "changes",
    [
        {"answer_providers": []},
        {"answer_providers": ["gemini", "gemini"]},
        {"answer_providers": ["gemini", "openai", "gemini"]},
        {"repeats": 0},
        {"repeats": 6},
        {"agent_version": "v3"},
        {"prompt_ids": []},
        {"prompt_ids": ["p01", "p01"]},
        {"category": "Ear Buds"},
        {"max_model_calls": 0},
        {"surprise": True},
    ],
)
def test_run_config_rejects_bad_values(changes: dict) -> None:
    values = {"category": "earbuds", "answer_providers": ["gemini"], **changes}
    with pytest.raises(ValidationError):
        RunConfig(**values)
