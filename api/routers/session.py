"""Session router — create, reset, and inspect sessions.

Endpoints
---------
- ``GET  /api/session``       → current session summary (SessionState)
- ``POST /api/session/reset`` → create a new session
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, Request

from api.dependencies import get_session
from api.models import SessionResetResponse, SessionState
from api.session_data import SessionData
from api.session_store import SessionStore

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
async def reset_session(request: Request) -> SessionResetResponse:
    """Create a brand-new session (NO auto-archive).

    The old session stays in the store until TTL eviction.
    Use ``POST /api/session/current/archive`` to explicitly archive.
    """
    store: SessionStore = request.app.state.store
    old_sid = request.headers.get("X-Session-Id", "")
    new_sid = store.create()
    return SessionResetResponse(
        old_session=old_sid,
        new_session=new_sid,
        archived=None,
    )
