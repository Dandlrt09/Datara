"""Files router — upload, list, preview, and delete session files.

Endpoints
---------
- ``POST   /api/files/upload``               → upload a file (multipart)
- ``GET    /api/files``                       → list all files
- ``DELETE /api/files/{filename}``            → remove a file
- ``GET    /api/files/{filename}/preview``    → preview first N rows
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile

from api.dependencies import get_session
from api.models import ErrorCode, ErrorResponse, FileMetadata
from api.session_data import SessionData

router = APIRouter(
    prefix="/api/files",
    tags=["files"],
    dependencies=[Depends(get_session)],
)


# ─── Disk persistence helpers ────────────────────────────────────────


def _upload_path(uploads_dir: Path, session_id: str, filename: str) -> Path:
    """Return the filesystem path for a session's uploaded file."""
    return uploads_dir / session_id / filename


def _save_upload(uploads_dir: Path, session_id: str, filename: str, content: bytes) -> None:
    """Persist raw file bytes to ``uploads/{session_id}/{filename}``."""
    if not session_id:
        return
    path = _upload_path(uploads_dir, session_id, filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _remove_upload(uploads_dir: Path, session_id: str, filename: str) -> None:
    """Remove a persisted file from disk."""
    if not session_id:
        return
    path = _upload_path(uploads_dir, session_id, filename)
    if path.exists():
        path.unlink()


# ─── Helpers ─────────────────────────────────────────────────────────


def _file_meta_from_store(session: SessionData, filename: str) -> FileMetadata:
    """Build a ``FileMetadata`` from a filename in the session's FileService."""
    fd = session.file_service.get_file(filename)
    if fd is None:
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    return FileMetadata(
        filename=fd.filename,
        display_name=fd.display_name,
        sheet_name=fd.sheet_name,
        size_bytes=fd.size_bytes,
        rows=fd.rows,
        columns=fd.columns,
        dtypes=fd.dtypes,
        loaded_at=fd.loaded_at or datetime.now(),
    )


# ─── Upload ──────────────────────────────────────────────────────────


@router.post("/upload", status_code=201)
async def upload_file(
    request: Request,
    session: SessionData = Depends(get_session),
    file: UploadFile = File(..., description="The file to upload"),
    sheet_name: str = Form("", description="Sheet name for Excel files"),
    replace: bool = Query(False, description="Replace existing file with same name"),
) -> FileMetadata:
    """Upload a CSV, Excel, JSON, or TSV file.

    Returns ``201`` with file metadata on success.  Returns ``409`` if
    the filename already exists and ``replace`` is not set.  Returns
    ``400`` on validation errors (unsupported type, empty file, etc.).
    """
    filename = file.filename or "unknown"
    content = await file.read()
    sid = request.headers.get("X-Session-Id", "")

    svc = session.file_service

    # ── Duplicate check ──────────────────────────────────────────
    existing = svc.get_file(filename)
    if existing is not None and not replace:
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(
                error=f"Duplicate filename: {filename}",
                code=ErrorCode.CONFLICT,
            ).model_dump(),
        )

    # ── Replace old if requested ─────────────────────────────────
    if replace and existing is not None:
        svc.remove_file(filename)

    # ── Parse & store ────────────────────────────────────────────
    success, result = svc.load_from_bytes(filename, content)

    if not success:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error=str(result),
                code=ErrorCode.BAD_REQUEST,
            ).model_dump(),
        )

    # ── Persist to disk ──────────────────────────────────────────
    fd = result  # FileData
    _save_upload(request.app.state.uploads_dir, sid, fd.filename, content)

    return FileMetadata(
        filename=fd.filename,
        display_name=fd.display_name,
        sheet_name=fd.sheet_name,
        size_bytes=fd.size_bytes,
        rows=fd.rows,
        columns=fd.columns,
        dtypes=fd.dtypes,
        loaded_at=fd.loaded_at,
    )


# ─── List ────────────────────────────────────────────────────────────


@router.get("")
async def list_files(
    session: SessionData = Depends(get_session),
) -> list[FileMetadata]:
    """Return metadata for every loaded file."""
    return [_file_meta_from_store(session, name) for name in session.file_service.get_filenames()]


# ─── Delete ──────────────────────────────────────────────────────────


@router.delete("/{filename}", status_code=204)
async def delete_file(
    filename: str,
    request: Request,
    session: SessionData = Depends(get_session),
) -> None:
    """Remove a file from the session.  Returns ``404`` if not found."""
    if session.file_service.get_file(filename) is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error=f"File not found: {filename}",
                code=ErrorCode.NOT_FOUND,
            ).model_dump(),
        )
    session.file_service.remove_file(filename)

    # Also remove from disk
    sid = request.headers.get("X-Session-Id", "")
    _remove_upload(request.app.state.uploads_dir, sid, filename)


# ─── Preview ─────────────────────────────────────────────────────────


@router.get("/{filename}/preview")
async def preview_file(
    filename: str,
    session: SessionData = Depends(get_session),
    rows: int = Query(10, ge=1, le=100, description="Number of preview rows"),
) -> dict:
    """Return a structured preview of the first *rows* of a file."""
    fd = session.file_service.get_file(filename)
    if fd is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error=f"File not found: {filename}",
                code=ErrorCode.NOT_FOUND,
            ).model_dump(),
        )

    preview_df = fd.df.head(rows)
    return {
        "filename": filename,
        "columns": list(fd.df.columns),
        "dtypes": fd.dtypes,
        "total_rows": fd.rows,
        "preview": preview_df.to_dict(orient="records"),
    }
