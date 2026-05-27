from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class ErrorCode(str, Enum):
    """Standard error codes returned by the API."""

    BAD_REQUEST = "BAD_REQUEST"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    SESSION_EXPIRED = "SESSION_EXPIRED"


class ErrorResponse(BaseModel):
    """Uniform error body returned on non-2xx responses.

    Schema::

        {"error": "Human-readable message", "code": "ERROR_CODE"}
    """

    error: str
    code: ErrorCode
