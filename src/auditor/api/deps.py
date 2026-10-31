"""FastAPI dependencies: a database session per request, and the authenticated client."""

import uuid
from collections.abc import Callable, Iterator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from auditor.api.errors import ApiError
from auditor.api.security import find_client_by_key
from auditor.config import Settings
from auditor.llm.types import LLMClient

# auto_error=False: we raise our own 401 so the body has our error format and the
# response carries WWW-Authenticate, as HTTP requires for a 401.
bearer = HTTPBearer(auto_error=False)


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_client_factory(request: Request) -> Callable[[], LLMClient]:
    return request.app.state.client_factory


SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
ClientFactoryDep = Annotated[Callable[[], LLMClient], Depends(get_client_factory)]


def current_client_id(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> uuid.UUID:
    """The ID of the client whose Bearer key was sent, or a 401."""
    client = find_client_by_key(session, credentials.credentials) if credentials else None
    if client is None:
        raise ApiError(
            401,
            "unauthorized",
            "missing or invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return client.id


ClientIdDep = Annotated[uuid.UUID, Depends(current_client_id)]
