"""Tests for ``ArchiveService`` — CRUD, atomic writes, corrupt JSON, edge cases.

Uses ``tmp_path`` for isolated temp directories per test.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from time import time

import pytest

from models import ChatMessage
from models.session_archive import ArchiveDataset, SessionArchive
from services.archive_service import ArchiveService


# ─── Helpers ──────────────────────────────────────────────────────────


def make_archive(archive_id: str, name: str, msg_count: int = 2) -> SessionArchive:
    """Build a ``SessionArchive`` with dummy data for testing."""
    return SessionArchive(
        archive_id=archive_id,
        name=name,
        original_session_id="orig-session-1",
        archived_at=time(),
        message_count=msg_count,
        datasets=[
            ArchiveDataset(
                filename="ventas.csv",
                columns=["mes", "ventas"],
                rows=100,
                dtypes={"mes": "object", "ventas": "int64"},
                preview_rows=[["Ene", 100], ["Feb", 200]],
                is_large=False,
            ),
        ],
        messages=[
            ChatMessage(role="user", content="Hola", timestamp=datetime.now()),
            ChatMessage(role="assistant", content="Mundo", timestamp=datetime.now()),
        ]
        if msg_count > 0
        else [],
        provider="Gemini (gemini-2.5-flash)",
    )


# ─── ArchiveService Tests ─────────────────────────────────────────────


class TestArchiveService:
    """Unit tests for all ArchiveService CRUD operations."""

    def test_create_and_list(self, tmp_path: Path):
        svc = ArchiveService(tmp_path / "archives")
        archive = make_archive("archive-001", "Sesión 1")
        svc.save_archive(archive)

        summaries = svc.list_archives()
        assert len(summaries) == 1
        assert summaries[0].archive_id == "archive-001"
        assert summaries[0].name == "Sesión 1"
        assert summaries[0].message_count == 2
        assert summaries[0].datasets == ["ventas.csv"]

    def test_get_archive(self, tmp_path: Path):
        svc = ArchiveService(tmp_path / "archives")
        archive = make_archive("archive-002", "Mi análisis")
        svc.save_archive(archive)

        loaded = svc.get_archive("archive-002")
        assert loaded is not None
        assert loaded.archive_id == "archive-002"
        assert loaded.name == "Mi análisis"
        assert loaded.message_count == 2
        assert len(loaded.messages) == 2
        assert loaded.messages[0].role == "user"
        assert loaded.messages[0].content == "Hola"
        assert len(loaded.datasets) == 1
        assert loaded.datasets[0].filename == "ventas.csv"

    def test_get_archive_unknown_returns_none(self, tmp_path: Path):
        svc = ArchiveService(tmp_path / "archives")
        assert svc.get_archive("does-not-exist") is None

    def test_list_empty_dir(self, tmp_path: Path):
        svc = ArchiveService(tmp_path / "archives")
        assert svc.list_archives() == []

    def test_list_sorted_desc_by_archived_at(self, tmp_path: Path):
        svc = ArchiveService(tmp_path / "archives")
        old = make_archive("a-old", "Old", msg_count=1)
        old.archived_at = 1000.0
        svc.save_archive(old)

        new = make_archive("a-new", "New", msg_count=1)
        new.archived_at = 2000.0
        svc.save_archive(new)

        summaries = svc.list_archives()
        assert [s.archive_id for s in summaries] == ["a-new", "a-old"]

    def test_delete_existing_returns_true(self, tmp_path: Path):
        svc = ArchiveService(tmp_path / "archives")
        archive = make_archive("archive-003", "To Delete")
        svc.save_archive(archive)

        assert svc.delete_archive("archive-003") is True
        assert svc.get_archive("archive-003") is None
        assert svc.list_archives() == []

    def test_delete_nonexistent_returns_false(self, tmp_path: Path):
        svc = ArchiveService(tmp_path / "archives")
        assert svc.delete_archive("i-dont-exist") is False

    def test_rename_updates_name(self, tmp_path: Path):
        svc = ArchiveService(tmp_path / "archives")
        archive = make_archive("archive-004", "Sesión 1")
        svc.save_archive(archive)

        renamed = svc.rename_archive("archive-004", "Mi análisis final")
        assert renamed is not None
        assert renamed.name == "Mi análisis final"

        # Verify persisted to disk
        loaded = svc.get_archive("archive-004")
        assert loaded is not None
        assert loaded.name == "Mi análisis final"

    def test_rename_nonexistent_returns_none(self, tmp_path: Path):
        svc = ArchiveService(tmp_path / "archives")
        assert svc.rename_archive("ghost", "New name") is None

    def test_next_archive_name_starts_at_one(self, tmp_path: Path):
        svc = ArchiveService(tmp_path / "archives")
        assert svc._next_archive_name() == "Sesión 1"

    def test_next_archive_name_increments(self, tmp_path: Path):
        svc = ArchiveService(tmp_path / "archives")
        a1 = make_archive("a1", "Sesión 1")
        svc.save_archive(a1)
        assert svc._next_archive_name() == "Sesión 2"

        a2 = make_archive("a2", "Sesión 2")
        svc.save_archive(a2)
        assert svc._next_archive_name() == "Sesión 3"

    def test_next_archive_name_skips_non_matching(self, tmp_path: Path):
        svc = ArchiveService(tmp_path / "archives")
        a1 = make_archive("a1", "Custom name")
        svc.save_archive(a1)
        # Non-matching names are ignored for the counter
        assert svc._next_archive_name() == "Sesión 1"


# ─── Resilience Tests ────────────────────────────────────────────────


class TestArchiveServiceResilience:
    """Edge cases: corrupt files, empty dirs, atomic writes."""

    def test_corrupt_json_skipped_with_warning(self, tmp_path: Path, caplog: pytest.LogCaptureFixture):
        """Corrupt JSON should be skipped during scan, with a warning logged."""
        archive_dir = tmp_path / "archives"
        archive_dir.mkdir()

        # Write a valid archive
        valid = make_archive("valid-001", "Valid")
        path = archive_dir / "valid-001.json"
        path.write_text(json.dumps(valid.to_dict(), ensure_ascii=False), encoding="utf-8")

        # Write a corrupt JSON file
        corrupt_path = archive_dir / "corrupt.json"
        corrupt_path.write_text("{this is not json", encoding="utf-8")

        # Also write a partially valid file (wrong structure)
        bad_schema = archive_dir / "bad-schema.json"
        bad_schema.write_text(json.dumps({"key": "value"}), encoding="utf-8")

        caplog.set_level(logging.WARNING)
        svc = ArchiveService(archive_dir)

        # Only the valid archive should be in the index
        assert svc.get_archive("valid-001") is not None
        assert svc.get_archive("corrupt") is None

        # List should only show the valid one
        summaries = svc.list_archives()
        assert len(summaries) == 1
        assert summaries[0].archive_id == "valid-001"

        # Warning should be logged for both corrupt files
        assert len([r for r in caplog.records if r.levelno >= logging.WARNING]) >= 2

    def test_get_corrupt_direct_returns_none(self, tmp_path: Path):
        """Directly getting a corrupt archive returns None (skip), not a crash."""
        archive_dir = tmp_path / "archives"
        archive_dir.mkdir()
        path = archive_dir / "broken.json"
        path.write_text("{not json", encoding="utf-8")

        svc = ArchiveService(archive_dir)
        result = svc.get_archive("broken")
        assert result is None

    def test_atomic_write_creates_valid_file(self, tmp_path: Path):
        """After atomic write, the file must be valid JSON."""
        svc = ArchiveService(tmp_path / "archives")
        archive = make_archive("atomic-test", "Atomic")
        svc.save_archive(archive)

        # Check the file on disk directly
        path = tmp_path / "archives" / "atomic-test.json"
        assert path.exists()
        assert path.suffix == ".json"

        # The .tmp file should NOT exist after successful write
        tmp_file = path.with_suffix(".tmp")
        assert not tmp_file.exists()

        # File should be valid JSON
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["archive_id"] == "atomic-test"
        assert data["name"] == "Atomic"

    def test_recover_on_restart(self, tmp_path: Path):
        """Archives survive service recreation (simulates server restart)."""
        archive_dir = tmp_path / "archives"

        # First session
        svc1 = ArchiveService(archive_dir)
        a1 = make_archive("survive-1", "Sesión 1")
        svc1.save_archive(a1)

        # "Restart" — create a new instance
        svc2 = ArchiveService(archive_dir)
        summaries = svc2.list_archives()
        assert len(summaries) == 1
        assert summaries[0].archive_id == "survive-1"

        loaded = svc2.get_archive("survive-1")
        assert loaded is not None
        assert loaded.name == "Sesión 1"
        assert len(loaded.messages) == 2

    def test_archive_dir_created_automatically(self, tmp_path: Path):
        """ArchiveService should create the directory if it doesn't exist."""
        non_existent = tmp_path / "does-not-exist-yet"
        svc = ArchiveService(non_existent)
        assert non_existent.is_dir()
        assert svc.list_archives() == []


class TestArchiveServiceThreadSafety:
    """Basic concurrency tests for ArchiveService."""

    def test_concurrent_save(self, tmp_path: Path):
        """Multiple saves should not interfere (each archive has its own file)."""
        import concurrent.futures

        svc = ArchiveService(tmp_path / "archives")

        def _save(n: int) -> str:
            aid = f"concurrent-{n:03d}"
            arc = make_archive(aid, f"Sesión {n}")
            svc.save_archive(arc)
            return aid

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            futs = [pool.submit(_save, i) for i in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futs)]

        assert len(results) == 20
        summaries = svc.list_archives()
        assert len(summaries) == 20
