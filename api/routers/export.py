"""Export router — download charts, dataframes, and conversations.

Endpoints
---------
- ``GET /api/export/{message_id}/chart``  → chart HTML (for Plotly.js)
- ``GET /api/export/{message_id}/data``   → dataframe as CSV
- ``GET /api/export/session``             → conversation as plain text
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse

import pandas as pd
from io import StringIO

from api.dependencies import get_session
from api.session_data import SessionData
from services import ExportService

router = APIRouter(
    prefix="/api/export",
    tags=["export"],
    dependencies=[Depends(get_session)],
)


def _get_message(session: SessionData, message_id: int):
    """Return a chat message by index or raise 404."""
    if message_id < 0 or message_id >= len(session.chat_messages):
        raise HTTPException(
            status_code=404,
            detail=f"Message {message_id} not found",
        )
    return session.chat_messages[message_id]


@router.get("/{message_id:int}/chart")
async def export_chart(
    message_id: int,
    session: SessionData = Depends(get_session),
):
    """Return the Plotly chart HTML for a message.

    The client renders this with Plotly.js and can use
    ``Plotly.downloadImage()`` to export as PNG.
    """
    msg = _get_message(session, message_id)
    if not msg.figure_json:
        raise HTTPException(
            status_code=404,
            detail=f"Message {message_id} has no figure",
        )
    return HTMLResponse(content=msg.figure_json)


@router.get("/{message_id:int}/data")
async def export_data(
    message_id: int,
    session: SessionData = Depends(get_session),
):
    """Return the dataframe for a message as a CSV download."""
    msg = _get_message(session, message_id)
    if not msg.dataframe_json:
        raise HTTPException(
            status_code=404,
            detail=f"Message {message_id} has no dataframe",
        )

    # Convert stored JSON (split orient) back to CSV
    df = pd.read_json(StringIO(msg.dataframe_json), orient="split")
    csv_bytes = ExportService.dataframe_to_csv(df)

    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=export_{message_id}.csv",
        },
    )


@router.get("/session")
async def export_session(
    session: SessionData = Depends(get_session),
):
    """Return the full conversation as a plain-text download."""
    text = ExportService.conversation_to_text(session.chat_messages)

    return Response(
        content=text,
        media_type="text/plain",
        headers={
            "Content-Disposition": "attachment; filename=conversacion.txt",
        },
    )
