"""The public API with Groq: choosing it for a run, and the verifier fallback on
/v1/verify. Existing routes and response shapes are unchanged."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from auditor.api.app import create_app
from auditor.api.security import create_api_client
from auditor.llm.errors import ProviderTimeoutError
from auditor.llm.fake import ScriptedClient

from ..audit.fakes import make_settings
from .test_api import ANSWER_TEXT, GOOD_SCRIPT

FALLBACK = {
    "verifier_provider": "groq",
    "verifier_model": "groq-model",
    "verifier_fallback_provider": "gemini",
    "verifier_fallback_model": "gemini-model",
}


def make_api(seeded: sessionmaker[Session], main_script, fallback_script=None, **settings):
    with seeded.begin() as session:
        _, key = create_api_client(session, "client-a")
    fallback_factory = (
        (lambda: ScriptedClient(fallback_script, model="gemini-model"))
        if fallback_script is not None
        else (lambda: None)
    )
    app = create_app(
        make_settings(llm_max_retries=0, **settings),
        seeded,
        lambda: ScriptedClient(main_script, model="groq-model"),
        fallback_factory,
    )
    return TestClient(app), {"Authorization": f"Bearer {key}"}


def test_verify_uses_the_fallback_when_groq_times_out(seeded: sessionmaker[Session]) -> None:
    http, headers = make_api(
        seeded, [ProviderTimeoutError("Groq request timed out")], GOOD_SCRIPT, **FALLBACK
    )

    response = http.post("/v1/verify", json={"text": ANSWER_TEXT}, headers=headers)

    assert response.status_code == 200
    answer = response.json()
    assert answer["status"] == "verified"
    assert answer["verifier_model"] == "gemini-model"
    failed = answer["usage"]["fallback_from"]
    assert (failed["provider"], failed["model"], failed["timed_out"]) == (
        "groq",
        "groq-model",
        True,
    )


def test_verify_without_a_fallback_keeps_todays_504(seeded: sessionmaker[Session]) -> None:
    http, headers = make_api(seeded, [ProviderTimeoutError("Groq request timed out")])

    response = http.post("/v1/verify", json={"text": ANSWER_TEXT}, headers=headers)

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "provider_timeout"


@pytest.mark.parametrize(
    "providers",
    [["groq"], ["gemini", "groq"], ["gemini", "openai", "groq"]],
)
def test_runs_accept_groq_and_up_to_three_providers(
    seeded: sessionmaker[Session], providers: list[str]
) -> None:
    http, headers = make_api(seeded, GOOD_SCRIPT)
    body = {"category": "earbuds", "prompt_ids": ["p01"], "answer_providers": providers}

    response = http.post("/v1/audit-runs", json=body, headers={**headers, "Idempotency-Key": "k1"})

    assert response.status_code == 202
    assert response.json()["config"]["answer_providers"] == providers


@pytest.mark.parametrize("providers", [["groq", "groq"], ["mistral"], []])
def test_runs_reject_duplicate_unknown_or_no_providers(
    seeded: sessionmaker[Session], providers: list[str]
) -> None:
    http, headers = make_api(seeded, GOOD_SCRIPT)
    body = {"category": "earbuds", "prompt_ids": ["p01"], "answer_providers": providers}

    response = http.post("/v1/audit-runs", json=body, headers={**headers, "Idempotency-Key": "k1"})

    assert response.status_code == 422
