"""Chat router — message, history, and conversation lifecycle.

Endpoints
---------
- ``POST   /api/chat/message``  → send a question, get an AI analysis
- ``GET    /api/chat/history``  → full conversation history
- ``DELETE /api/chat/clear``    → wipe all messages
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends

logger = logging.getLogger(__name__)

from api.dependencies import get_session
from api.models import MessageRequest, MessageResponse
from api.session_data import SessionData
from models import ChatMessage
from services import ExportService

router = APIRouter(
    prefix="/api/chat",
    tags=["chat"],
    dependencies=[Depends(get_session)],
)

# ── Mock mode — bypass LLM for UI testing ─────────────────────────────


def _is_mock_mode() -> bool:
    """Lazy check so tests can override via environ / monkeypatch."""
    return os.getenv("CHAT_MOCK_MODE", "true").lower() in ("1", "true", "yes")


@router.post("/message", response_model=MessageResponse)
async def send_message(
    body: MessageRequest,
    session: SessionData = Depends(get_session),
) -> MessageResponse:
    """Send a chat message and receive an AI-powered analysis.

    The LLM response may include text, a Plotly figure, and/or a
    dataframe.  Returns ``400`` for empty messages and a fallback
    ``MessageResponse`` with ``error=true`` if the LLM is not configured.
    """
    message = body.message.strip()
    if not message:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # ── Persist user message ────────────────────────────────────
    user_msg = ChatMessage(role="user", content=message)
    session.chat_messages.append(user_msg)

    # ── Mock mode — canned response for UI testing ──────────────
    if _is_mock_mode():
        logger.info("MOCK MODE: respondiendo a '%s'", message[:50])
        content = ("¡Hola! ¿Cómo estás? Soy Datara, tu asistente de análisis de datos. "
                   "Estoy en modo de pruebas — decime qué te gustaría probar.")
        assistant_msg = ChatMessage(
            role="assistant",
            content=content,
        )
        session.chat_messages.append(assistant_msg)
        resp = MessageResponse(
            message_id=len(session.chat_messages) - 1,
            role="assistant",
            content=content,
        )
        logger.info("MOCK MODE: respondiendo message_id=%d", resp.message_id)
        return resp

    # ── Guard: LLM not configured → early return ────────────────
    if not session.llm_service.is_configured:
        return MessageResponse(
            message_id=len(session.chat_messages) - 1,
            role="assistant",
            content="API key de Gemini no configurada. "
            "Andá a Settings y cargá tu API key de "
            "https://aistudio.google.com/apikey",
            error=True,
        )

    # ── Execute analysis ────────────────────────────────────────
    files = session.file_service.list_files()
    history = list(session.chat_messages)

    result = session.code_executor.analyze(
        question=message,
        files=files,
        chat_history=history,
    )

    # ── Build artifacts ─────────────────────────────────────────
    figure_html = (
        ExportService.chart_to_html(result.figure)
        if result.has_figure and result.figure is not None
        else None
    )
    dataframe_json = (
        result.dataframe.to_json(orient="split")
        if result.has_dataframe and result.dataframe is not None
        else None
    )

    # ── Persist assistant message ───────────────────────────────
    assistant_msg = ChatMessage(
        role="assistant",
        content=result.text,
        figure_json=figure_html,
        dataframe_json=dataframe_json,
        error=not result.success,
    )
    session.chat_messages.append(assistant_msg)

    msg_id = len(session.chat_messages) - 1

    return MessageResponse(
        message_id=msg_id,
        role="assistant",
        content=result.text,
        figure_html=figure_html,
        dataframe_json=dataframe_json,
        error=not result.success,
    )


@router.get("/history")
async def get_history(
    session: SessionData = Depends(get_session),
) -> list[MessageResponse]:
    """Return every message in the conversation, oldest first."""
    return [
        MessageResponse(
            message_id=i,
            role=msg.role,
            content=msg.content,
            figure_html=msg.figure_json,
            dataframe_json=msg.dataframe_json,
            error=msg.error,
        )
        for i, msg in enumerate(session.chat_messages)
    ]


@router.delete("/clear", status_code=204)
async def clear_chat(
    session: SessionData = Depends(get_session),
) -> None:
    """Remove all chat messages from the session."""
    session.chat_messages.clear()
