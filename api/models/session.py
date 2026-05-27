from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from api.models.chat import MessageResponse


class SessionState(BaseModel):
    """Current session summary returned by ``GET /api/session``."""

    session_id: str
    file_count: int
    files: list[str]
    message_count: int
    user_message_count: int = 0
    assistant_message_count: int = 0
    provider: str


class SessionResetResponse(BaseModel):
    """Response returned by ``POST /api/session/reset``.

    If the old session had messages or files, ``archived`` contains the
    newly created archive metadata.
    """

    old_session: str
    new_session: str
    archived: Optional[ArchiveResponse] = None


# ─── Archive models ──────────────────────────────────────────────────


class ArchiveResponse(BaseModel):
    """Minimal archive metadata (returned from archive / reset endpoints)."""

    archive_id: str
    name: str
    archived_at: float


class ArchiveDatasetMeta(BaseModel):
    """Column metadata for an archived dataset — NOT the full DataFrame."""

    filename: str
    columns: list[str]
    rows: int
    dtypes: dict[str, str]
    preview_rows: list[list]
    is_large: bool


class ArchiveSummary(BaseModel):
    """Lightweight archive entry returned by ``GET /api/session/archived``."""

    archive_id: str
    name: str
    archived_at: float
    message_count: int
    datasets: list[str]  # filenames only


class ArchiveDetail(BaseModel):
    """Full archive detail returned by ``GET /api/session/archived/{id}``."""

    archive_id: str
    name: str
    original_session_id: str
    archived_at: float
    message_count: int
    datasets: list[ArchiveDatasetMeta]
    messages: list[MessageResponse]
    provider: str


class RenameRequest(BaseModel):
    """Request body for ``PATCH /api/session/archived/{id}``."""

    name: str


class ArchiveCurrentRequest(BaseModel):
    """Optional body for ``POST /api/session/current/archive``."""

    archive_id: Optional[str] = None



