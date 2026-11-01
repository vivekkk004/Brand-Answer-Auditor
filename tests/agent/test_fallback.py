from collections.abc import Sequence

import pytest

from auditor.agent.fallback import Verifier, verify_with_fallback
from auditor.catalogue.repository import InMemoryCatalogue
from auditor.catalogue.schema import CatalogueData
from auditor.enums import ErrorType, Provider
from auditor.llm.errors import (
    PermanentProviderError,
    ProviderConfigError,
    ProviderTimeoutError,
    TransientProviderError,
)
from auditor.llm.fake import ScriptedClient

from .test_verifier import ANSWER, FACTS, PRICE_CLAIM, reply, submit

GOOD = [FACTS, submit(PRICE_CLAIM)]


def run(
    demo_catalogue: CatalogueData,
    main_script: Sequence,
    fallback_script: Sequence | None,
    **options,
):
    main = ScriptedClient(main_script, model="groq-model")
    fallback = ScriptedClient(fallback_script or [], model="gemini-model")
    outcome = verify_with_fallback(
        main=Verifier(Provider.GROQ, main),
        fallback=Verifier(Provider.GEMINI, fallback) if fallback_script is not None else None,
        answer_text=ANSWER,
        catalogue=InMemoryCatalogue(demo_catalogue),
        market="IN",
        max_retries=0,
        sleep=lambda _: None,
        **options,
    )
    return outcome, main, fallback


def test_main_success_never_touches_the_fallback(demo_catalogue: CatalogueData) -> None:
    outcome, _, fallback = run(demo_catalogue, GOOD, GOOD)
    assert outcome.result.ok
    assert (outcome.provider, outcome.result.model) == (Provider.GROQ, "groq-model")
    assert outcome.fallback_from is None
    assert fallback.calls == []


@pytest.mark.parametrize(
    "failure",
    [
        TransientProviderError("Groq 429: rate limited"),
        ProviderTimeoutError("Groq request timed out"),
        PermanentProviderError("Groq 400: tool_use_failed"),
    ],
)
def test_a_provider_failure_switches_to_the_fallback(
    demo_catalogue: CatalogueData, failure: Exception
) -> None:
    outcome, main, fallback = run(demo_catalogue, [failure], GOOD)

    assert outcome.result.ok
    assert (outcome.provider, outcome.result.model) == (Provider.GEMINI, "gemini-model")
    failed = outcome.fallback_from
    assert failed.provider == Provider.GROQ
    assert failed.result.error_type == ErrorType.PROVIDER
    assert failed.result.timed_out == isinstance(failure, ProviderTimeoutError)
    # The fallback starts again from the user message, not from the main conversation.
    assert len(fallback.calls[0].messages) == 1
    assert len(main.calls) == 1


def test_bad_model_output_does_not_fall_back(demo_catalogue: CatalogueData) -> None:
    outcome, _, fallback = run(demo_catalogue, [reply(text="Looks fine.")] * 4, GOOD)
    assert outcome.result.error_type == ErrorType.PROMPT
    assert outcome.provider == Provider.GROQ
    assert fallback.calls == []


def test_config_errors_are_raised_not_hidden_by_the_fallback(
    demo_catalogue: CatalogueData,
) -> None:
    with pytest.raises(ProviderConfigError):
        run(demo_catalogue, [ProviderConfigError("Groq 401: invalid key")], GOOD)


def test_the_caller_can_refuse_the_fallback(demo_catalogue: CatalogueData) -> None:
    outcome, _, fallback = run(
        demo_catalogue, [TransientProviderError("busy")], GOOD, can_fall_back=lambda first: False
    )
    assert not outcome.result.ok
    assert outcome.provider == Provider.GROQ
    assert fallback.calls == []


def test_without_a_fallback_the_failure_is_returned(demo_catalogue: CatalogueData) -> None:
    outcome, _, _ = run(demo_catalogue, [TransientProviderError("busy")], None)
    assert outcome.result.error_type == ErrorType.PROVIDER
    assert outcome.fallback_from is None
