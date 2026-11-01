"""HTTP routes. Each handler parses the request and calls one function in services.py."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Header, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from auditor.api import services
from auditor.api.deps import (
    ClientFactoryDep,
    ClientIdDep,
    FallbackClientFactoryDep,
    SessionDep,
    SettingsDep,
)
from auditor.api.errors import ApiError
from auditor.api.schemas import (
    AnswerOut,
    ReviewDecision,
    ReviewItemList,
    ReviewItemOut,
    RunList,
    RunOut,
    VerifyRequest,
)
from auditor.audit.run_config import RunConfig
from auditor.enums import ReviewStatus, RunStatus

router = APIRouter()


@router.get("/healthz")
def healthz(request: Request) -> JSONResponse:
    """Liveness plus a database ping: an API that cannot reach its database is not healthy."""
    try:
        with request.app.state.session_factory() as session:
            session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return JSONResponse(content={"status": "ok"})


@router.post("/v1/verify", response_model=AnswerOut)
def verify(
    body: VerifyRequest,
    client_id: ClientIdDep,
    session: SessionDep,
    settings: SettingsDep,
    client_factory: ClientFactoryDep,
    fallback_client_factory: FallbackClientFactoryDep,
) -> AnswerOut:
    return services.verify_text(
        session, client_id, body, settings, client_factory, fallback_client_factory
    )


@router.post("/v1/audit-runs", status_code=202, response_model=RunOut)
def create_audit_run(
    body: RunConfig,
    client_id: ClientIdDep,
    session: SessionDep,
    response: Response,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> RunOut:
    if not idempotency_key or len(idempotency_key) > 200:
        raise ApiError(
            400, "missing_idempotency_key", "send an Idempotency-Key header (1-200 characters)"
        )
    run, replayed = services.create_run(session, client_id, body, idempotency_key)
    response.headers["Location"] = f"/v1/audit-runs/{run.id}"
    if replayed:
        response.status_code = 200
        response.headers["Idempotent-Replayed"] = "true"
    return services.run_out(run)


@router.get("/v1/audit-runs", response_model=RunList)
def list_audit_runs(
    client_id: ClientIdDep,
    session: SessionDep,
    status: RunStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RunList:
    return services.list_runs(session, client_id, status, limit, offset)


@router.get("/v1/audit-runs/{run_id}", response_model=RunOut)
def get_audit_run(run_id: uuid.UUID, client_id: ClientIdDep, session: SessionDep) -> RunOut:
    return services.get_run(session, client_id, run_id)


@router.get("/v1/answers/{answer_id}", response_model=AnswerOut)
def get_answer(answer_id: uuid.UUID, client_id: ClientIdDep, session: SessionDep) -> AnswerOut:
    return services.get_answer(session, client_id, answer_id)


@router.get("/v1/review-items", response_model=ReviewItemList)
def list_review_items(
    client_id: ClientIdDep,
    session: SessionDep,
    status: ReviewStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ReviewItemList:
    return services.list_review_items(session, client_id, status, limit, offset)


@router.patch("/v1/review-items/{item_id}", response_model=ReviewItemOut)
def decide_review_item(
    item_id: uuid.UUID, body: ReviewDecision, client_id: ClientIdDep, session: SessionDep
) -> ReviewItemOut:
    return services.decide_review_item(session, client_id, item_id, body)
