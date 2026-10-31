import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from auditor.api import services
from auditor.api.app import create_app
from auditor.api.security import create_api_client
from auditor.db.session import make_engine, make_session_factory
from auditor.llm.errors import PermanentProviderError, ProviderConfigError, ProviderTimeoutError
from auditor.llm.fake import ScriptedClient, tool_call
from auditor.llm.types import ModelResponse

from ..audit.fakes import CONTRADICTED_PRICE, make_settings

ANSWER_TEXT = "The Zentro Air 2 costs ₹6,999 in India, and it sounds great."
RUN_BODY = {"category": "earbuds", "prompt_ids": ["p01"], "answer_providers": ["gemini"]}


def reply(*calls, text: str | None = None) -> ModelResponse:
    return ModelResponse(text=text, tool_calls=calls)


GOOD_SCRIPT = [
    reply(tool_call("get_brand_facts", "f1", brand_id="zentro")),
    reply(tool_call("submit_claims", "s1", claims=[CONTRADICTED_PRICE])),
]


@dataclass
class Api:
    http: TestClient
    key_a: str
    key_b: str
    factory: sessionmaker[Session]
    # What the next /v1/verify call gets as its model: a script, or an error to raise.
    script: Sequence[ModelResponse | Exception] = field(default_factory=lambda: GOOD_SCRIPT)
    factory_error: Exception | None = None

    def headers(self, key: str | None = None, **extra: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {key or self.key_a}", **extra}

    def verify(self, key: str | None = None, **body):
        body.setdefault("text", ANSWER_TEXT)
        return self.http.post("/v1/verify", json=body, headers=self.headers(key))

    def create_run(self, body=None, key: str | None = None, idempotency_key: str = "k1"):
        return self.http.post(
            "/v1/audit-runs",
            json=RUN_BODY if body is None else body,
            headers=self.headers(key, **{"Idempotency-Key": idempotency_key}),
        )


@pytest.fixture
def api(seeded: sessionmaker[Session]) -> Api:
    with seeded.begin() as session:
        _, key_a = create_api_client(session, "client-a")
        _, key_b = create_api_client(session, "client-b")
    holder: dict[str, Api] = {}

    def client_factory() -> ScriptedClient:
        current = holder["api"]
        if current.factory_error is not None:
            raise current.factory_error
        return ScriptedClient(current.script)

    # No retries, so a failing script needs one scripted error and no real sleeping.
    app = create_app(make_settings(llm_max_retries=0), seeded, client_factory)
    holder["api"] = Api(TestClient(app), key_a, key_b, seeded)
    return holder["api"]


def error(response) -> dict:
    return response.json()["error"]


# --- Health ---


def test_healthz_ok(api: Api) -> None:
    response = api.http.get("/healthz")
    assert (response.status_code, response.json()) == (200, {"status": "ok"})


def test_healthz_is_503_when_the_database_is_down(tmp_path: Path) -> None:
    broken = make_session_factory(make_engine(f"sqlite:///{(tmp_path / 'no' / 'db').as_posix()}"))
    response = TestClient(create_app(make_settings(), broken)).get("/healthz")
    assert (response.status_code, response.json()) == (503, {"status": "unavailable"})


# --- Auth ---


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Basic dXNlcjpwYXNz"},
        {"Authorization": "Bearer not-a-key"},
        {"Authorization": "Bearer baa_wrong-but-well-formed"},
    ],
)
def test_missing_or_bad_key_is_401(api: Api, headers: dict) -> None:
    response = api.http.get("/v1/review-items", headers=headers)
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert error(response)["code"] == "unauthorized"


def test_auth_is_checked_before_the_body(api: Api) -> None:
    response = api.http.post("/v1/verify", json={"nonsense": True})
    assert response.status_code == 401


# --- Validation ---


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("post", "/v1/verify", {"text": "x", "surprise": 1}),
        ("post", "/v1/verify", {"text": ""}),
        ("post", "/v1/verify", {"text": "x", "market": "usa"}),
        ("get", "/v1/review-items?status=maybe", None),
        ("get", "/v1/review-items?limit=500", None),
        ("get", "/v1/answers/not-a-uuid", None),
        ("patch", f"/v1/review-items/{uuid.uuid4()}", {"decision": "approved"}),
    ],
)
def test_invalid_requests_are_422(api: Api, method: str, path: str, body) -> None:
    response = api.http.request(method, path, json=body, headers=api.headers())
    assert response.status_code == 422
    assert error(response)["code"] == "validation_error"


# --- /v1/verify ---


def test_verify_success_returns_claims_and_exchanges(api: Api) -> None:
    response = api.verify(market="IN")

    assert response.status_code == 200
    answer = response.json()
    assert answer["status"] == "verified"
    assert answer["brands_mentioned"] == ["zentro"]
    (claim,) = answer["claims"]
    assert ANSWER_TEXT[claim["start"] : claim["end"]] == claim["quote"]
    assert claim["label"] == "contradicted"
    assert [m["role"] for m in answer["exchanges"]] == ["user", "assistant", "tool", "assistant"]


@pytest.mark.parametrize(
    ("script", "status", "code", "error_type"),
    [
        ([PermanentProviderError("400 bad request")], 502, "provider_error", "provider"),
        ([ProviderTimeoutError("slow")], 504, "provider_timeout", "provider"),
        ([reply(text="Looks fine.")] * 4, 502, "invalid_model_output", "prompt"),
        ([RuntimeError("secret internals")], 500, "internal_error", "code"),
    ],
)
def test_verify_failures_are_stored_and_mapped(
    api: Api, script: list, status: int, code: str, error_type: str
) -> None:
    api.script = script
    response = api.verify()

    assert response.status_code == status
    body = error(response)
    assert (body["code"], body["error_type"]) == (code, error_type)
    assert "secret internals" not in response.text

    stored = api.http.get(f"/v1/answers/{body['answer_id']}", headers=api.headers()).json()
    assert stored["status"] == "verification_failed"
    assert stored["error_type"] == error_type


def test_verify_without_a_configured_verifier_is_503(api: Api) -> None:
    api.factory_error = ProviderConfigError("no verifier provider given: set VERIFIER_PROVIDER")
    response = api.verify()

    assert response.status_code == 503
    body = error(response)
    assert body["code"] == "verifier_not_configured"
    stored = api.http.get(f"/v1/answers/{body['answer_id']}", headers=api.headers()).json()
    assert stored["error_type"] == "config"


# --- /v1/audit-runs ---


def test_create_run_is_202_with_location(api: Api) -> None:
    response = api.create_run()

    assert response.status_code == 202
    run = response.json()
    assert run["status"] == "queued"
    assert run["config"]["repeats"] == 3  # defaults are filled in
    assert response.headers["Location"] == f"/v1/audit-runs/{run['id']}"
    assert "Idempotent-Replayed" not in response.headers


def test_create_run_needs_an_idempotency_key(api: Api) -> None:
    response = api.http.post("/v1/audit-runs", json=RUN_BODY, headers=api.headers())
    assert response.status_code == 400
    assert error(response)["code"] == "missing_idempotency_key"


def test_same_key_and_same_body_replays_the_same_run(api: Api) -> None:
    first = api.create_run().json()
    # Same meaning, different spelling: key order changed and a default written out.
    replay = api.create_run({**dict(reversed(list(RUN_BODY.items()))), "repeats": 3})

    assert replay.status_code == 200
    assert replay.headers["Idempotent-Replayed"] == "true"
    assert replay.json()["id"] == first["id"]


def test_same_key_with_a_different_body_is_409(api: Api) -> None:
    api.create_run()
    response = api.create_run({**RUN_BODY, "repeats": 5})
    assert response.status_code == 409
    assert error(response)["code"] == "idempotency_conflict"


def test_keys_are_scoped_per_client(api: Api) -> None:
    first = api.create_run().json()
    other = api.create_run(key=api.key_b)
    assert other.status_code == 202
    assert other.json()["id"] != first["id"]


def test_a_lost_race_on_the_same_key_returns_the_winner(
    api: Api, monkeypatch: pytest.MonkeyPatch
) -> None:
    winner = api.create_run().json()
    real_lookup = services.find_run_by_key
    calls = {"n": 0}

    def lookup_misses_once(*args):
        # Simulate the race: our first lookup runs before the other request commits.
        calls["n"] += 1
        return None if calls["n"] == 1 else real_lookup(*args)

    monkeypatch.setattr(services, "find_run_by_key", lookup_misses_once)
    response = api.create_run()

    assert response.status_code == 200
    assert response.json()["id"] == winner["id"]
    assert calls["n"] == 2  # missed, hit the unique constraint, looked up again


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({**RUN_BODY, "category": "toasters"}, "no_matching_prompts"),
        ({**RUN_BODY, "prompt_ids": ["p01", "p99"]}, "no_matching_prompts"),
        ({**RUN_BODY, "max_model_calls": 6000}, "validation_error"),
        ({**RUN_BODY, "answer_providers": ["gemini", "gemini"]}, "validation_error"),
        ({**RUN_BODY, "surprise": True}, "validation_error"),
    ],
)
def test_bad_run_requests_are_422(api: Api, body: dict, code: str) -> None:
    response = api.create_run(body)
    assert response.status_code == 422
    assert error(response)["code"] == code


def test_get_run(api: Api) -> None:
    created = api.create_run().json()
    response = api.http.get(f"/v1/audit-runs/{created['id']}", headers=api.headers())
    assert response.status_code == 200
    assert response.json() == created


# --- Isolation between clients ---


def test_other_clients_ids_are_404(api: Api) -> None:
    run_id = api.create_run().json()["id"]
    answer_id = api.verify().json()["id"]
    other = api.headers(api.key_b)

    for path in (f"/v1/audit-runs/{run_id}", f"/v1/answers/{answer_id}"):
        response = api.http.get(path, headers=other)
        assert response.status_code == 404
        assert error(response)["code"] == "not_found"
    assert api.http.get(f"/v1/audit-runs/{uuid.uuid4()}", headers=api.headers()).status_code == 404


# --- Review queue ---


def test_review_flow(api: Api) -> None:
    api.verify(market="IN")

    open_items = api.http.get("/v1/review-items?status=open", headers=api.headers()).json()
    (item,) = open_items["items"]
    assert item["claim"]["label"] == "contradicted"
    path = f"/v1/review-items/{item['id']}"

    # Another client cannot see or decide it.
    assert api.http.get("/v1/review-items", headers=api.headers(api.key_b)).json()["items"] == []
    other = api.http.patch(path, json={"decision": "confirmed"}, headers=api.headers(api.key_b))
    assert other.status_code == 404

    decided = api.http.patch(
        path, json={"decision": "confirmed", "note": "Price is wrong."}, headers=api.headers()
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "confirmed"
    assert decided.json()["note"] == "Price is wrong."
    assert decided.json()["resolved_at"] is not None

    again = api.http.patch(path, json={"decision": "dismissed"}, headers=api.headers())
    assert again.status_code == 409
    assert error(again)["code"] == "already_decided"

    by_status = {
        status: len(
            api.http.get(f"/v1/review-items?status={status}", headers=api.headers()).json()["items"]
        )
        for status in ("open", "confirmed", "dismissed")
    }
    assert by_status == {"open": 0, "confirmed": 1, "dismissed": 0}
