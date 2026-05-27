"""Test fixtures for API router integration tests.

Provides a ``TestClient`` wired to the real dependency chain
(``SessionStore`` + ``SessionData``) so tests exercise the same
code paths as production, with isolated in-memory state.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers import api_router
from api.session_data import SessionData
from api.session_store import SessionStore
from services.archive_service import ArchiveService


@pytest.fixture
def store() -> SessionStore:
    """A clean ``SessionStore`` with a 1-hour TTL."""
    return SessionStore(ttl=3600)


@pytest.fixture
def session_id() -> str:
    """Fixed UUID used as the ``X-Session-Id`` header value in tests."""
    return "test-session-uuid-1234"


@pytest.fixture
def session_data() -> SessionData:
    """A ``SessionData`` with default (unconfigured) services.

    ``llm_service.is_configured`` starts ``False`` and
    ``code_executor`` is a real ``CodeExecutor`` (backed by the
    unconfigured LLM).  Tests that exercise LLM paths should mock
    ``code_executor.analyze``.
    """
    data = SessionData()
    data.llm_service.api_key = ""  # ensure deterministic (ignore .env)
    data.llm_service.model = "models/gemini-test"
    return data


@pytest.fixture
def archive_service(tmp_path: Path) -> ArchiveService:
    """A clean ``ArchiveService`` backed by a temporary directory."""
    return ArchiveService(tmp_path / "archives")


@pytest.fixture
def client(
    tmp_path: Path,
    store: SessionStore,
    session_id: str,
    session_data: SessionData,
    archive_service: ArchiveService,
) -> Generator[TestClient, None, None]:
    """A ``TestClient`` with the real router stack and a pre-seeded session.

    The app uses a minimal lifespan that sets ``app.state.store`` to the
    injected *store* fixture.  The *session_data* fixture is inserted
    into the store under *session_id*.

    Endpoints protected by ``Depends(get_session)`` will resolve the real
    session from the store as long as the request carries
    ``X-Session-Id: test-session-uuid-1234``.
    """

    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        app.state.store = store
        app.state.archive_service = archive_service
        app.state.uploads_dir = tmp_path / "uploads"
        yield

    app = FastAPI(lifespan=_lifespan)
    app.include_router(api_router)

    # Health check (mirrors what create_app() provides)
    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "datara-api"}

    # Seed the test session
    store._sessions[session_id] = session_data  # noqa: SLF001

    with TestClient(app) as c:
        yield c
