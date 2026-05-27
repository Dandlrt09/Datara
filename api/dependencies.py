from __future__ import annotations

from typing import Optional

from fastapi import Header, HTTPException, Request

from api.session_data import SessionData
from api.session_store import SessionStore
from services.archive_service import ArchiveService


async def get_store(request: Request) -> SessionStore:
    """Return the SessionStore instance from app state.

    Uses the app's ``state.store`` attribute, which must be set during
    the FastAPI lifespan.
    """
    return request.app.state.store


async def get_session(
    request: Request,
    x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
) -> SessionData:
    """Extract and resolve ``X-Session-Id`` header into a ``SessionData``.

    Raises ``404`` if the header is missing or the session has been
    evicted (expired or never created).
    """
    store: SessionStore = request.app.state.store

    if x_session_id is None:
        raise HTTPException(
            status_code=400,
            detail={"error": "X-Session-Id header is required", "code": "BAD_REQUEST"},
        )

    session = store.get(x_session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Session not found or expired. Create a new one with POST /api/session/reset",
                "code": "SESSION_EXPIRED",
            },
        )

    return session


async def get_archive_service(request: Request) -> ArchiveService:
    """Return the ``ArchiveService`` from app state.

    The service is initialised during the FastAPI lifespan.
    Raises ``500`` if it is not configured.
    """
    svc: Optional[ArchiveService] = getattr(request.app.state, "archive_service", None)
    if svc is None:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Archive service not configured",
                "code": "SERVER_ERROR",
            },
        )
    return svc
