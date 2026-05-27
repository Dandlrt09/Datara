from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class SettingsRequest(BaseModel):
    """Request body for ``PUT /api/settings``."""

    api_key: Optional[str] = None
    model: Optional[str] = None


class SettingsResponse(BaseModel):
    """Response returning the current LLM configuration."""

    model: str
    provider: str
    is_configured: bool
