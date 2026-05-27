"""Disk-based JSON archive CRUD with atomic writes and thread safety.

Usage::

    svc = ArchiveService("archives/")
    archive = SessionArchive(...)
    svc.save_archive(archive)

    for summary in svc.list_archives():
        print(summary.name)
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Optional

from models.session_archive import SessionArchive

logger = logging.getLogger(__name__)


class ArchiveSummary:
    """Lightweight read-only summary returned by :meth:`list_archives`."""

    __slots__ = ("archive_id", "name", "archived_at", "message_count", "datasets")

    def __init__(
        self,
        archive_id: str,
        name: str,
        archived_at: float,
        message_count: int,
        datasets: list[str],
    ) -> None:
        self.archive_id = archive_id
        self.name = name
        self.archived_at = archived_at
        self.message_count = message_count
        self.datasets = datasets  # filenames only


class ArchiveService:
    """CRUD over a directory of per-archive JSON files.

    * Thread-safe via ``threading.Lock()``.
    * Atomic writes (write to ``.tmp`` then ``os.rename()``).
    * Warm-starts by scanning the directory on ``__init__``.
    * Corrupt JSON files are logged and skipped (not a crash).
    """

    def __init__(self, archive_dir: str | Path) -> None:
        self._path = Path(archive_dir)
        self._path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._index: dict[str, SessionArchive] = {}
        self._scan_existing()
        recovered = len(self._index)
        logger.info(
            "ArchiveService initialised at %s (%d archive%s recovered)",
            self._path,
            recovered,
            "s" if recovered != 1 else "",
        )

    # ─── Public API ──────────────────────────────────────────────────

    def list_archives(self) -> list[ArchiveSummary]:
        """Return all archives sorted by ``archived_at`` DESC (newest first)."""
        with self._lock:
            archives = list(self._index.values())
        archives.sort(key=lambda a: a.archived_at, reverse=True)
        return [
            ArchiveSummary(
                archive_id=a.archive_id,
                name=a.name,
                archived_at=a.archived_at,
                message_count=a.message_count,
                datasets=[d.filename for d in a.datasets],
            )
            for a in archives
        ]

    def get_archive(self, archive_id: str) -> Optional[SessionArchive]:
        """Return the full archive, or ``None`` if not found.

        First checks the in-memory index.  If missing, falls back to
        reading directly from disk (handles index staleness after a
        manual file-system change).
        """
        with self._lock:
            archive = self._index.get(archive_id)
            if archive is not None:
                return archive

        # Fallback: try reading from disk (index may be stale).
        path = self._archive_path(archive_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            archive = SessionArchive.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning("Failed to read archive %s: %s", archive_id, exc)
            return None

        with self._lock:
            self._index[archive_id] = archive
        return archive

    def save_archive(self, archive: SessionArchive) -> None:
        """Persist *archive* to disk atomically (tmp → rename).

        The file is written to ``{archive_id}.tmp`` first, then renamed
        to ``{archive_id}.json``.  This prevents partial writes from
        being visible on the filesystem.
        """
        data = archive.to_dict()
        path = self._archive_path(archive.archive_id)
        self._atomic_write(path, data)
        with self._lock:
            self._index[archive.archive_id] = archive

    def delete_archive(self, archive_id: str) -> bool:
        """Remove the archive file from disk.

        Returns ``True`` if the file existed and was deleted.
        """
        path = self._archive_path(archive_id)
        with self._lock:
            if not path.exists():
                return False
            path.unlink()
            self._index.pop(archive_id, None)
            return True

    def rename_archive(self, archive_id: str, new_name: str) -> Optional[SessionArchive]:
        """Update the human-readable *name* of an archive.

        Returns the updated ``SessionArchive`` or ``None`` if the
        archive does not exist.
        """
        with self._lock:
            archive = self._index.get(archive_id)
            if archive is None:
                return None
            archive.name = new_name
            path = self._archive_path(archive_id)
            self._atomic_write(path, archive.to_dict())
            return archive

    # ─── Internal helpers ───────────────────────────────────────────

    def _next_archive_name(self) -> str:
        """Generate the next auto-incremented name like ``Sesión 1``.

        Scans existing names for the ``Sesión N`` pattern, finds the
        highest *N*, and returns ``Sesión {N + 1}``.
        """
        with self._lock:
            max_n = 0
            for a in self._index.values():
                name = a.name
                if name.startswith("Sesión "):
                    try:
                        n = int(name.split(" ")[-1])
                        if n > max_n:
                            max_n = n
                    except (ValueError, IndexError):
                        pass
            return f"Sesión {max_n + 1}"

    def _archive_path(self, archive_id: str) -> Path:
        """Filesystem path for the JSON file of an archive."""
        return self._path / f"{archive_id}.json"

    def _scan_existing(self) -> None:
        """Rebuild in-memory index by scanning ``*.json`` files on disk.

        Corrupt entries are logged as warnings and skipped — the server
        continues normally.
        """
        for path in sorted(self._path.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                archive = SessionArchive.from_dict(data)
                self._index[archive.archive_id] = archive
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                logger.warning("Skipping corrupt archive file %s: %s", path.name, exc)

    def _atomic_write(self, path: Path, data: dict) -> None:
        """Write *data* as JSON to *path* atomically.

        1. Serialise to ``{path}.tmp``.
        2. Replace ``.json`` with ``.tmp`` (``os.replace`` is atomic on
           the same filesystem and works on both POSIX and Windows).
        """
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        os.replace(tmp, path)
