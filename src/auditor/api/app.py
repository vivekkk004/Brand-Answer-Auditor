"""The FastAPI application.

Run it with:  uvicorn auditor.api.app:create_app --factory
"""

from collections.abc import Callable

from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker

from auditor.api.errors import install_error_handlers
from auditor.api.routes import router
from auditor.config import Settings
from auditor.db.session import make_engine, make_session_factory
from auditor.llm.factory import build_fallback_verifier_client, build_verifier_client
from auditor.llm.types import LLMClient


def create_app(
    settings: Settings | None = None,
    session_factory: sessionmaker[Session] | None = None,
    client_factory: Callable[[], LLMClient] | None = None,
    fallback_client_factory: Callable[[], LLMClient | None] | None = None,
) -> FastAPI:
    """Build the app. Every dependency can be passed in, so tests use a test database and
    a scripted model without touching globals or the network.

    The verifier client is built per request (client_factory), so a missing verifier
    setting gives a 503 on /v1/verify instead of stopping the whole API from starting.
    """
    settings = settings or Settings()
    app = FastAPI(title="Brand Answer Auditor", version="0.1.0")
    app.state.settings = settings
    app.state.session_factory = session_factory or make_session_factory(
        make_engine(settings.database_url)
    )
    app.state.client_factory = client_factory or (lambda: build_verifier_client(settings))
    # The optional fallback verifier; returns None when none is configured.
    app.state.fallback_client_factory = fallback_client_factory or (
        lambda: build_fallback_verifier_client(settings)
    )
    install_error_handlers(app)
    app.include_router(router)
    return app
