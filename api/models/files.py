from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class FileMetadata(BaseModel):
    """Public metadata about an uploaded file."""

    filename: str
    display_name: str
    sheet_name: str = ""
    size_bytes: int = 0
    rows: int = 0
    columns: int = 0
    dtypes: dict[str, str] = {}
    loaded_at: datetime


class FilePreview(BaseModel):
    """HTML table preview of the file's first rows."""

    filename: str
    preview_html: str


class UploadResponse(BaseModel):
    """Response returned after a successful file upload."""

    filename: str
    display_name: str
    rows: int
    columns: int
    message: str = "Archivo cargado correctamente."
