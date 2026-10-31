from collections.abc import Sequence

import pytest

from auditor.catalogue.loader import PROMPTS_FILE, load_prompts
from auditor.catalogue.repository import InMemoryCatalogue
from auditor.catalogue.schema import CatalogueData
from auditor.config import Settings
from auditor.evals.dataset import DATASET_FILE, Dataset, load_dataset
from auditor.llm.fake import tool_call
from auditor.llm.types import Message, ModelResponse, TokenUsage, ToolSpec

from ..conftest import DEMO_DIR


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


@pytest.fixture
def catalogue(demo_catalogue: CatalogueData) -> InMemoryCatalogue:
    return InMemoryCatalogue(demo_catalogue)


@pytest.fixture
def prompt_ids() -> set[str]:
    return {prompt.prompt_id for prompt in load_prompts(DEMO_DIR / PROMPTS_FILE)}


@pytest.fixture
def dataset(catalogue: InMemoryCatalogue, prompt_ids: set[str]) -> Dataset:
    return load_dataset(DEMO_DIR / DATASET_FILE, catalogue, prompt_ids)


class OracleClient:
    """A fake model that "knows" the gold labels: it looks up every brand, then submits
    the gold claims for the answer it is shown. Useful to test the whole eval pipeline
    end to end. Its scores are perfect by construction and mean nothing about a model."""

    model = "oracle"

    def __init__(self, dataset: Dataset, brand_ids: Sequence[str]) -> None:
        self.gold_by_text = {answer.text: answer.gold for answer in dataset.answers}
        self.brand_ids = list(brand_ids)

    def generate(
        self,
        *,
        system: str,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec],
        required_tool: str | None = None,
    ) -> ModelResponse:
        tokens = TokenUsage(input_tokens=100, output_tokens=10)
        if not any(message.role == "tool" for message in messages):
            calls = tuple(
                tool_call("get_brand_facts", f"f{i}", brand_id=brand_id)
                for i, brand_id in enumerate(self.brand_ids)
            )
            return ModelResponse(text=None, tool_calls=calls, tokens=tokens)

        user_message = messages[0].content
        text = user_message.split("<ai_answer>\n", 1)[1].rsplit("\n</ai_answer>", 1)[0]
        claims = [
            {
                "quote": gold.quote,
                "brand_id": gold.brand_id,
                "attribute": "feature",
                "label": gold.label.value,
                "fact_ids": list(gold.fact_ids),
                "rationale": "oracle",
            }
            for gold in self.gold_by_text[text]
        ]
        submit = tool_call("submit_claims", "s1", claims=claims)
        return ModelResponse(text=None, tool_calls=(submit,), tokens=tokens)
