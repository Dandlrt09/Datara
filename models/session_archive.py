from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from models import ChatMessage


@dataclass
class ArchiveDataset:
    """Metadata about a dataset archived from a session.

    Stores column info, shape, dtypes, and a small preview — NOT the
    full DataFrame (DataFrames are ephemeral; users re-upload on restore).
    """

    filename: str
    columns: list[str]
    rows: int
    dtypes: dict[str, str]
    preview_rows: list[list]
    is_large: bool = False
    stored_session_id: str = ""
    """The session ID that had this file on disk at archive time.
    
    On restore, the system looks for ``uploads/{stored_session_id}/{filename}``
    to re-attach the raw file.  Empty means no file was persisted.
    """

    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "columns": self.columns,
            "rows": self.rows,
            "dtypes": self.dtypes,
            "preview_rows": self.preview_rows,
            "is_large": self.is_large,
            "stored_session_id": self.stored_session_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ArchiveDataset:
        return cls(
            filename=data["filename"],
            columns=data["columns"],
            rows=data["rows"],
            dtypes=data["dtypes"],
            preview_rows=data["preview_rows"],
            is_large=data.get("is_large", False),
            stored_session_id=data.get("stored_session_id", ""),
        )


@dataclass
class SessionArchive:
    """Complete snapshot of an archived session, persisted as JSON on disk.

    Contains all chat messages, file metadata, provider info, and a
    human-friendly name.  Serialized via :meth:`to_dict` / :meth:`from_dict`.
    """

    archive_id: str
    name: str
    original_session_id: str
    archived_at: float
    message_count: int
    datasets: list[ArchiveDataset]
    messages: list[ChatMessage]
    provider: str

    def to_dict(self) -> dict:
        return {
            "archive_id": self.archive_id,
            "name": self.name,
            "original_session_id": self.original_session_id,
            "archived_at": self.archived_at,
            "message_count": self.message_count,
            "datasets": [ds.to_dict() for ds in self.datasets],
            "messages": [_message_to_dict(m) for m in self.messages],
            "provider": self.provider,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SessionArchive:
        return cls(
            archive_id=data["archive_id"],
            name=data["name"],
            original_session_id=data["original_session_id"],
            archived_at=data["archived_at"],
            message_count=data["message_count"],
            datasets=[ArchiveDataset.from_dict(ds) for ds in data["datasets"]],
            messages=[_message_from_dict(m) for m in data["messages"]],
            provider=data["provider"],
        )


# ─── Helper serializers for ChatMessage ───────────────────────────────


def _message_to_dict(msg: ChatMessage) -> dict:
    return {
        "role": msg.role,
        "content": msg.content,
        "figure_json": msg.figure_json,
        "dataframe_json": msg.dataframe_json,
        "timestamp": msg.timestamp.isoformat(),
        "error": msg.error,
    }


def _message_from_dict(data: dict) -> ChatMessage:
    ts = data.get("timestamp")
    return ChatMessage(
        role=data["role"],
        content=data["content"],
        figure_json=data.get("figure_json"),
        dataframe_json=data.get("dataframe_json"),
        timestamp=datetime.fromisoformat(ts) if ts else datetime.now(),
        error=data.get("error", False),
    )
