from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from threading import Lock
from time import time
from typing import TYPE_CHECKING, Optional

from api.session_data import SessionData
from models.session_archive import ArchiveDataset, SessionArchive
from services.llm_service import DEFAULT_MODEL, LLMService

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from services.archive_service import ArchiveService
    from services.config_service import ConfigService

# Default TTL: 1 hour (in seconds)
DEFAULT_TTL_SECONDS: int = 3600


class SessionStore:
    """In-memory dict[str, SessionData] with TTL eviction and thread safety.

    Each session is keyed by a UUID v4 string.  The store is:

    - **Thread-safe**: all public methods acquire ``_lock``.
    - **Self-evicting**: ``get()`` and ``create()`` call ``_evict_expired()``
      which removes any session whose ``last_active`` is older than ``ttl``.
    - **Isolated**: every ``SessionData`` holds independent ``FileService``,
      ``LLMService``, ``CodeExecutor``, ``chat_messages``, and
      ``dashboard_items``.
    - **Global LLM config**: ``api_key`` and ``model`` set via Settings are
      stored at store level and applied to every new session, so user
      preferences survive session resets.

    Usage::

        store = SessionStore(ttl=3600)
        sid = store.create()
        data = store.get(sid)   # → SessionData | None
        new_sid = store.reset(sid)
    """

    def __init__(self, ttl: int = DEFAULT_TTL_SECONDS, config_service: Optional[ConfigService] = None) -> None:
        self._sessions: dict[str, SessionData] = {}
        self._ttl = ttl
        self._lock = Lock()
        self._config = config_service
        # Global LLM config — survives session resets, applied to every new session
        # Priority: ConfigService (explicit user save via Settings) > env var > empty
        config_key = self._config.api_key if self._config else ""
        env_key = os.getenv("GEMINI_API_KEY", "")
        self._global_api_key: str = config_key or env_key
        env_model = os.getenv("GEMINI_MODEL", "")
        self._global_model: str = env_model or (self._config.model if self._config else DEFAULT_MODEL)

    # ─── Global LLM config ──────────────────────────────────────────

    def set_global_api_key(self, api_key: str) -> None:
        """Persist an API key at store level so new sessions pick it up."""
        self._global_api_key = api_key
        if self._config:
            self._config.api_key = api_key

    def clear_global_api_key(self) -> None:
        """Remove the user-saved API key override.

        New sessions will fall back to the env var ``GEMINI_API_KEY``
        (or be unconfigured if no env var is set).
        """
        self._global_api_key = os.getenv("GEMINI_API_KEY", "")
        if self._config:
            self._config.clear_api_key()

    def set_global_model(self, model: str) -> None:
        """Persist a model name at store level so new sessions pick it up."""
        self._global_model = model
        if self._config:
            self._config.model = model

    def _make_llm_service(self) -> LLMService:
        """Create an LLMService with the current global config."""
        return LLMService(api_key=self._global_api_key, model=self._global_model)

    # ─── Public API ──────────────────────────────────────────────────

    def get(self, sid: str) -> Optional[SessionData]:
        """Return the session data for *sid*, or ``None`` if not found.

        Also evicts expired sessions and touches last_active.
        """
        with self._lock:
            self._evict_expired()
            data = self._sessions.get(sid)
            if data is not None:
                data.touch()
            return data

    def create(self) -> str:
        """Generate a new UUID, allocate a fresh SessionData, return the ID."""
        with self._lock:
            self._evict_expired()
            sid = str(uuid.uuid4())
            self._sessions[sid] = SessionData(llm_service=self._make_llm_service())
            return sid

    def reset(self, sid: str) -> Optional[str]:
        """Reset the session identified by *sid* and return a new UUID.

        1. Creates a brand-new UUID and ``SessionData``.
        2. Does **not** remove the old session (it will be TTL-evicted).
        3. Returns the new UUID.

        If *sid* doesn't exist, it is ignored (a new session is still created).
        """
        with self._lock:
            self._evict_expired()
            new_sid = str(uuid.uuid4())
            self._sessions[new_sid] = SessionData(llm_service=self._make_llm_service())
            return new_sid

    def remove(self, sid: str) -> None:
        """Immediately remove a session."""
        with self._lock:
            self._sessions.pop(sid, None)

    @property
    def ttl(self) -> int:
        """Configured TTL in seconds."""
        return self._ttl

    @property
    def active_count(self) -> int:
        """Number of currently live (non-evicted) sessions."""
        with self._lock:
            self._evict_expired()
            return len(self._sessions)

    # ─── Archive support ────────────────────────────────────────────

    def archive_session(self, sid: str, archive_service: ArchiveService, archive_id: Optional[str] = None) -> SessionArchive:
        """Serialise *sid* session data into a ``SessionArchive`` and persist it.

        If *archive_id* is provided, UPDATES that existing archive instead
        of creating a new one (preserves name, original_session_id, archived_at).

        Raises ``ValueError`` if the session does not exist.
        The caller (router) is responsible for checking whether the
        session is empty before calling this method.
        """
        with self._lock:
            self._evict_expired()
            data = self._sessions.get(sid)
            if data is None:
                raise ValueError(f"Session not found: {sid}")
            messages = list(data.chat_messages)
            provider = data.llm_service.provider_info
            files = data.file_service.list_files()

        datasets = [
            ArchiveDataset(
                filename=fd.filename,
                columns=fd.df.columns.tolist(),
                rows=fd.rows,
                dtypes=fd.dtypes,
                preview_rows=fd.df.head(5).values.tolist(),
                is_large=fd.rows > 10000,
                stored_session_id=sid,
            )
            for fd in files
        ]

        if archive_id is not None:
            # ── Update existing archive ──────────────────────────────
            existing = archive_service.get_archive(archive_id)
            if existing is not None:
                archive = SessionArchive(
                    archive_id=existing.archive_id,
                    name=existing.name,
                    original_session_id=existing.original_session_id,
                    archived_at=time(),
                    message_count=len(messages),
                    datasets=datasets,
                    messages=messages,
                    provider=provider,
                )
            else:
                # Archive doesn't exist on disk — fall back to creating new
                archive = SessionArchive(
                    archive_id=archive_id,
                    name=archive_service._next_archive_name(),
                    original_session_id=sid,
                    archived_at=time(),
                    message_count=len(messages),
                    datasets=datasets,
                    messages=messages,
                    provider=provider,
                )
        else:
            archive = SessionArchive(
                archive_id=f"archive_{uuid.uuid4()}",
                name=archive_service._next_archive_name(),
                original_session_id=sid,
                archived_at=time(),
                message_count=len(messages),
                datasets=datasets,
                messages=messages,
                provider=provider,
            )
        archive_service.save_archive(archive)
        return archive

    def restore_archive(self, archive: SessionArchive, uploads_dir: str | Path = "") -> str:
        """Create a new session and load *archive* messages and files into it.

        If *uploads_dir* is provided, attempts to re-attach uploaded files
        from disk using ``stored_session_id`` on each ``ArchiveDataset``.

        Returns the new session ID.
        """
        with self._lock:
            self._evict_expired()
            new_sid = str(uuid.uuid4())
            data = SessionData(llm_service=self._make_llm_service())
            data.chat_messages = list(archive.messages)

            # Try to restore files from disk
            for ds in archive.datasets:
                if not ds.stored_session_id:
                    continue
                file_path = Path(uploads_dir) / ds.stored_session_id / ds.filename
                if file_path.is_file():
                    try:
                        content = file_path.read_bytes()
                        data.file_service.load_from_bytes(ds.filename, content)
                        # Re-persist to the new session's upload directory so
                        # subsequent archives of this session can find the file
                        # on disk using stored_session_id (= new_sid).
                        new_path = Path(uploads_dir) / new_sid / ds.filename
                        new_path.parent.mkdir(parents=True, exist_ok=True)
                        new_path.write_bytes(content)
                    except Exception:
                        logger.exception("Failed to restore file %s", ds.filename)

            self._sessions[new_sid] = data
            return new_sid

    # ─── Internal ───────────────────────────────────────────────────

    def _evict_expired(self) -> None:
        """Remove all sessions whose last_active is older than TTL.

        Caller MUST hold ``_lock``.
        """
        now = time()
        cutoff = now - self._ttl
        stale = [sid for sid, data in self._sessions.items() if data.last_active < cutoff]
        for sid in stale:
            del self._sessions[sid]
