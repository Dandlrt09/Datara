"""Archive router — CRUD for archived chat sessions.

Endpoints
---------
- ``GET    /api/session/archived``         → list all (ArchiveSummary[])
- ``GET    /api/session/archived/{id}``    → full detail (ArchiveDetail)
- ``POST   /api/session/current/archive``  → archive current session
- ``POST   /api/session/archived/{id}/restore`` → restore as active session
- ``DELETE /api/session/archived/{id}``    → 204
- ``PATCH  /api/session/archived/{id}``    → rename
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from api.dependencies import get_archive_service, get_store
from api.models import (
    ArchiveCurrentRequest,
    ArchiveDatasetMeta,
    ArchiveDetail,
    ArchiveResponse,
    ArchiveSummary,
    MessageResponse,
    RenameRequest,
)
from api.session_data import SessionData
from api.session_store import SessionStore
from services.archive_service import ArchiveService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/session", tags=["archive"])


# ─── GET /api/session/archived ────────────────────────────────────────


@router.get("/archived", response_model=list[ArchiveSummary])
async def list_archives(
    archive_service: ArchiveService = Depends(get_archive_service),
) -> list[ArchiveSummary]:
    """List all archived sessions, sorted newest first."""
    summaries = archive_service.list_archives()
    return [
        ArchiveSummary(
            archive_id=s.archive_id,
            name=s.name,
            archived_at=s.archived_at,
            message_count=s.message_count,
            datasets=s.datasets,
        )
        for s in summaries
    ]


# ─── GET /api/session/archived/{archive_id} ───────────────────────────


@router.get("/archived/{archive_id}", response_model=ArchiveDetail)
async def get_archive(
    archive_id: str,
    archive_service: ArchiveService = Depends(get_archive_service),
) -> ArchiveDetail:
    """Return full archive detail including all messages."""
    archive = archive_service.get_archive(archive_id)
    if archive is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "Archive not found", "code": "ARCHIVE_NOT_FOUND"},
        )
    return ArchiveDetail(
        archive_id=archive.archive_id,
        name=archive.name,
        original_session_id=archive.original_session_id,
        archived_at=archive.archived_at,
        message_count=archive.message_count,
        datasets=[
            ArchiveDatasetMeta(
                filename=ds.filename,
                columns=ds.columns,
                rows=ds.rows,
                dtypes=ds.dtypes,
                preview_rows=ds.preview_rows,
                is_large=ds.is_large,
            )
            for ds in archive.datasets
        ],
        messages=[
            MessageResponse(
                message_id=i,
                role=msg.role,
                content=msg.content,
                figure_html=msg.figure_json,
                dataframe_json=msg.dataframe_json,
                error=msg.error,
            )
            for i, msg in enumerate(archive.messages)
        ],
        provider=archive.provider,
    )


# ─── POST /api/session/current/archive ────────────────────────────────


@router.post("/current/archive", response_model=ArchiveResponse)
async def archive_current_session(
    request: Request,
    body: Optional[ArchiveCurrentRequest] = None,
    store: SessionStore = Depends(get_store),
    archive_service: ArchiveService = Depends(get_archive_service),
) -> ArchiveResponse:
    """Archive the current session (requires ``X-Session-Id``).

    If ``body.archive_id`` is provided, UPDATES that existing archive
    instead of creating a new one (replaces messages/datasets).

    Returns ``409`` if the session has no messages and no files.
    """
    sid = request.headers.get("X-Session-Id", "")
    if not sid:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "X-Session-Id header is required",
                "code": "BAD_REQUEST",
            },
        )

    data: Optional[SessionData] = store.get(sid)
    if data is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Session not found or expired",
                "code": "SESSION_EXPIRED",
            },
        )

    if len(data.chat_messages) == 0 and data.file_service.file_count == 0:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Session is empty (no messages and no files)",
                "code": "EMPTY_SESSION",
            },
        )

    archive_id = body.archive_id if body else None
    archive = store.archive_session(sid, archive_service, archive_id=archive_id)
    return ArchiveResponse(
        archive_id=archive.archive_id,
        name=archive.name,
        archived_at=archive.archived_at,
    )


# ─── POST /api/session/archived/{archive_id}/restore ──────────────────


@router.post("/archived/{archive_id}/restore")
async def restore_archive(
    archive_id: str,
    request: Request,
    store: SessionStore = Depends(get_store),
    archive_service: ArchiveService = Depends(get_archive_service),
) -> dict:
    """Restore an archived session as a new active session.

    Creates a fresh session, loads all messages, and returns metadata
    about the datasets that need re-uploading (``needed: true``).
    When the uploaded file exists on disk, it is automatically restored
    and ``needed`` is set to ``false``.
    """
    archive = archive_service.get_archive(archive_id)
    if archive is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "Archive not found", "code": "ARCHIVE_NOT_FOUND"},
        )

    uploads_dir = getattr(request.app.state, "uploads_dir", "")
    new_sid = store.restore_archive(archive, uploads_dir=uploads_dir)

    # Check which datasets were actually restored into the new session
    new_data = store.get(new_sid)
    restored_filenames = set()
    if new_data is not None:
        restored_filenames = set(new_data.file_service.get_filenames())

    return {
        "new_session_id": new_sid,
        "archive_name": archive.name,
        "datasets": [
            {
                "filename": ds.filename,
                "columns": ds.columns,
                "rows": ds.rows,
                "dtypes": ds.dtypes,
                "preview_rows": ds.preview_rows,
                "is_large": ds.is_large,
                "needed": ds.filename not in restored_filenames,
            }
            for ds in archive.datasets
        ],
        "messages": [
            {
                "message_id": i,
                "role": msg.role,
                "content": msg.content,
                "figure_html": msg.figure_json,
                "dataframe_json": msg.dataframe_json,
                "error": msg.error,
            }
            for i, msg in enumerate(archive.messages)
        ],
    }


# ─── DELETE /api/session/archived/{archive_id} ────────────────────────


@router.delete("/archived/{archive_id}", status_code=204)
async def delete_archive(
    archive_id: str,
    archive_service: ArchiveService = Depends(get_archive_service),
) -> None:
    """Delete an archived session from disk."""
    deleted = archive_service.delete_archive(archive_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={"error": "Archive not found", "code": "ARCHIVE_NOT_FOUND"},
        )


# ─── PATCH /api/session/archived/{archive_id} ─────────────────────────


@router.patch("/archived/{archive_id}", response_model=ArchiveDetail)
async def rename_archive(
    archive_id: str,
    body: RenameRequest,
    archive_service: ArchiveService = Depends(get_archive_service),
) -> ArchiveDetail:
    """Rename an archived session."""
    archive = archive_service.rename_archive(archive_id, body.name)
    if archive is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "Archive not found", "code": "ARCHIVE_NOT_FOUND"},
        )
    return ArchiveDetail(
        archive_id=archive.archive_id,
        name=archive.name,
        original_session_id=archive.original_session_id,
        archived_at=archive.archived_at,
        message_count=archive.message_count,
        datasets=[
            ArchiveDatasetMeta(
                filename=ds.filename,
                columns=ds.columns,
                rows=ds.rows,
                dtypes=ds.dtypes,
                preview_rows=ds.preview_rows,
                is_large=ds.is_large,
            )
            for ds in archive.datasets
        ],
        messages=[
            MessageResponse(
                message_id=i,
                role=msg.role,
                content=msg.content,
                figure_html=msg.figure_json,
                dataframe_json=msg.dataframe_json,
                error=msg.error,
            )
            for i, msg in enumerate(archive.messages)
        ],
        provider=archive.provider,
    )
