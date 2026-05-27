from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class MessageRequest(BaseModel):
    """Request body for ``POST /api/chat/message``."""

    message: str


class MessageResponse(BaseModel):
    """Response returned after processing a chat message."""

    message_id: int
    role: str = "assistant"
    content: str = ""
    figure_html: Optional[str] = None
    dataframe_json: Optional[str] = None
    error: bool = False
