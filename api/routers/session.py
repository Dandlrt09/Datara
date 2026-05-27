"""Session router — create, reset, and inspect sessions.

Endpoints
---------
- ``GET  /api/session``       → current session summary (SessionState)
- ``POST /api/session/reset`` → create a new session
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, Request

from api.dependencies import get_archive_service, get_session
from api.models import ArchiveResponse, SessionResetResponse, SessionState
from api.session_data import SessionData
from api.session_store import SessionStore
from services.archive_service import ArchiveService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/session", tags=["session"])


@router.get("", response_model=SessionState)
async def get_session_state(
    session: SessionData = Depends(get_session),
    x_session_id: str = Header(..., alias="X-Session-Id"),
) -> SessionState:
    """Return a summary of the current session (files, messages, provider).

    Requires a valid ``X-Session-Id`` header.
    """
    user_count = sum(1 for m in session.chat_messages if m.role == "user")
    assistant_count = sum(1 for m in session.chat_messages if m.role == "assistant")

    return SessionState(
        session_id=x_session_id,
        file_count=session.file_service.file_count,
        files=session.file_service.get_filenames(),
        message_count=len(session.chat_messages),
        user_message_count=user_count,
        assistant_message_count=assistant_count,
        provider=session.llm_service.provider_info,
    )


@router.post("/reset", response_model=SessionResetResponse)
async def reset_session(
    request: Request,
    archive_service: ArchiveService = Depends(get_archive_service),
) -> SessionResetResponse:
    """Reset the session, auto-archiving if it has messages or files."""
    store: SessionStore = request.app.state.store
    old_sid = request.headers.get("X-Session-Id", "")

    # Auto-archive the old session if it has content
    archived: Optional[ArchiveResponse] = None
    if old_sid:
        data = store.get(old_sid)
        if data is not None and (len(data.chat_messages) > 0 or data.file_service.file_count > 0):
            try:
                archive = store.archive_session(old_sid, archive_service)
                archived = ArchiveResponse(
                    archive_id=archive.archive_id,
                    name=archive.name,
                    archived_at=archive.archived_at,
                )
            except Exception:
                logger.exception("Failed to auto-archive session %s on reset", old_sid)

    new_sid = store.create()
    return SessionResetResponse(
        old_session=old_sid,
        new_session=new_sid,
        archived=archived,
    )
