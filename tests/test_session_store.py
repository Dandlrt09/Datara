"""Tests for SessionStore — TTL eviction, isolation, reset, edge cases."""

import time as time_module
from datetime import datetime
from unittest.mock import patch

import pytest

from api.session_data import SessionData
from api.session_store import SessionStore
from models import ChatMessage


class TestSessionStore:
    """SessionStore with in-memory dict, UUID keys, and TTL eviction."""

    def test_create_returns_valid_uuid(self):
        store = SessionStore(ttl=3600)
        sid = store.create()
        # UUID v4 is a 36-char hex string with 4 hyphens
        assert len(sid) == 36
        assert sid.count("-") == 4

    def test_get_returns_session_data(self):
        store = SessionStore(ttl=3600)
        sid = store.create()
        data = store.get(sid)
        assert isinstance(data, SessionData)

    def test_get_unknown_id_returns_none(self):
        store = SessionStore(ttl=3600)
        assert store.get("nonexistent-uuid") is None

    def test_get_empty_string_returns_none(self):
        store = SessionStore(ttl=3600)
        assert store.get("") is None

    def test_session_isolation(self):
        """Two sessions must have independent SessionData instances."""
        store = SessionStore(ttl=3600)
        sid_a = store.create()
        sid_b = store.create()

        data_a = store.get(sid_a)
        data_b = store.get(sid_b)

        # Different objects
        assert data_a is not data_b
        assert data_a.file_service is not data_b.file_service
        assert data_a.chat_messages is not data_b.chat_messages

        # Mutating one must not affect the other
        data_a.chat_messages.append("msg")  # type: ignore[arg-type]
        assert len(data_b.chat_messages) == 0

    def test_reset_returns_new_uuid(self):
        store = SessionStore(ttl=3600)
        old_sid = store.create()
        new_sid = store.reset(old_sid)

        assert new_sid != old_sid
        assert len(new_sid) == 36

    def test_reset_does_not_remove_old_session(self):
        """Old session remains accessible until TTL eviction."""
        store = SessionStore(ttl=3600)
        old_sid = store.create()
        old_data = store.get(old_sid)

        # Store something on old session
        old_data.chat_messages.append("hello")  # type: ignore[arg-type]

        store.reset(old_sid)

        # Old session should still be accessible
        retrieved = store.get(old_sid)
        assert retrieved is not None
        assert len(retrieved.chat_messages) == 1  # type: ignore[arg-type]

    def test_reset_unknown_id_still_creates_new_session(self):
        store = SessionStore(ttl=3600)
        new_sid = store.reset("nonexistent")
        assert store.get(new_sid) is not None

    def test_ttl_eviction_expired_session_returns_none(self):
        """A session created 31 minutes ago should be evicted with 30-min TTL."""
        store = SessionStore(ttl=1800)  # 30 min
        sid = store.create()

        # Freeze time 31 minutes into the future
        fake_now = time_module.time() + 1860
        with patch("api.session_store.time", return_value=fake_now):
            with patch("api.session_data.time", return_value=fake_now):
                assert store.get(sid) is None

    def test_ttl_eviction_before_cutoff_still_valid(self):
        """A session created 29 minutes ago should still be valid with 30-min TTL."""
        store = SessionStore(ttl=1800)
        sid = store.create()

        fake_now = time_module.time() + 1740  # 29 min
        with patch("api.session_store.time", return_value=fake_now):
            with patch("api.session_data.time", return_value=fake_now):
                assert store.get(sid) is not None

    def test_active_count(self):
        store = SessionStore(ttl=3600)
        assert store.active_count == 0
        store.create()
        assert store.active_count == 1
        store.create()
        assert store.active_count == 2

    def test_active_count_excludes_expired(self):
        store = SessionStore(ttl=1800)
        store.create()
        store.create()

        fake_now = time_module.time() + 1860
        with patch("api.session_store.time", return_value=fake_now):
            with patch("api.session_data.time", return_value=fake_now):
                # Both sessions have last_active < cutoff
                assert store.active_count == 0

    def test_remove_explicitly(self):
        store = SessionStore(ttl=3600)
        sid = store.create()
        assert store.get(sid) is not None
        store.remove(sid)
        assert store.get(sid) is None

    def test_remove_unknown_id_does_not_raise(self):
        store = SessionStore(ttl=3600)
        store.remove("nonexistent")  # should not raise

    def test_get_touches_last_active(self):
        """Calling get() should update the session's last_active timestamp."""
        store = SessionStore(ttl=3600)
        sid = store.create()
        store.get(sid)

        # Advance time slightly but not past TTL
        fake_now = time_module.time() + 60
        with patch("api.session_store.time", return_value=fake_now):
            with patch("api.session_data.time", return_value=fake_now):
                touched = store.get(sid)
                assert touched is not None
                # After touching, last_active should reflect the new time
                assert touched.last_active == fake_now

    def test_ttl_property(self):
        store = SessionStore(ttl=1800)
        assert store.ttl == 1800

    def test_create_increments_active_count(self):
        store = SessionStore(ttl=3600)
        sids = [store.create() for _ in range(5)]
        assert store.active_count == 5
        # Remove one
        store.remove(sids[2])
        assert store.active_count == 4

    def test_reset_old_session_ttl_independent(self):
        """After reset, old and new sessions have independent TTL timelines."""
        store = SessionStore(ttl=1800)
        old_sid = store.create()
        new_sid = store.reset(old_sid)

        # Verify both exist
        assert store.get(old_sid) is not None
        assert store.get(new_sid) is not None


# ─────────────────────────────────────────────────────────────────────
# Archive / Restore tests
# ─────────────────────────────────────────────────────────────────────


class TestSessionStoreArchive:
    """``archive_session`` and ``restore_archive`` on SessionStore."""

    def test_archive_session_creates_correct_archive(self, tmp_path):
        """Archive contains messages, file metadata, and provider info."""
        from services.archive_service import ArchiveService

        store = SessionStore()
        archive_svc = ArchiveService(tmp_path / "archives")

        sid = store.create()
        data = store.get(sid)
        assert data is not None

        # Add a message and a file
        data.chat_messages.append(ChatMessage(role="user", content="Hola", timestamp=datetime.now()))  # type: ignore[arg-type]
        data.chat_messages.append(ChatMessage(role="assistant", content="Mundo", timestamp=datetime.now()))  # type: ignore[arg-type]

        import pandas as pd
        from models.file_data import FileData
        df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        fd = FileData(filename="test.csv", df=df)
        data.file_service.add_file(fd)

        archive = store.archive_session(sid, archive_svc)

        assert archive.original_session_id == sid
        assert archive.message_count == 2
        assert len(archive.messages) == 2
        assert archive.messages[0].role == "user"
        assert archive.messages[0].content == "Hola"
        assert len(archive.datasets) == 1
        assert archive.datasets[0].filename == "test.csv"
        assert archive.datasets[0].columns == ["x", "y"]
        assert archive.datasets[0].rows == 3
        assert archive.provider != ""

    def test_archive_session_unknown_id_raises(self, tmp_path):
        from services.archive_service import ArchiveService

        store = SessionStore()
        archive_svc = ArchiveService(tmp_path / "archives")

        with pytest.raises(ValueError, match="Session not found"):
            store.archive_session("nonexistent", archive_svc)

    def test_archive_empty_session_still_works(self, tmp_path):
        """Even an empty session can be archived (router gates emptiness)."""
        from services.archive_service import ArchiveService

        store = SessionStore()
        archive_svc = ArchiveService(tmp_path / "archives")
        sid = store.create()

        archive = store.archive_session(sid, archive_svc)

        assert archive.message_count == 0
        assert archive.datasets == []
        assert len(archive.messages) == 0

        # Verify persisted
        loaded = archive_svc.get_archive(archive.archive_id)
        assert loaded is not None
        assert loaded.message_count == 0

    def test_restore_archive_creates_new_session(self, tmp_path):
        from services.archive_service import ArchiveService

        store = SessionStore()
        archive_svc = ArchiveService(tmp_path / "archives")

        # Create and save an archive
        from models.session_archive import ArchiveDataset, SessionArchive
        archive = SessionArchive(
            archive_id="restore-test-1",
            name="Sesión 1",
            original_session_id="orig-1",
            archived_at=1000.0,
            message_count=2,
            datasets=[],
            messages=[
                ChatMessage(role="user", content="Hola"),
                ChatMessage(role="assistant", content="Mundo"),
            ],
            provider="test",
        )
        archive_svc.save_archive(archive)

        new_sid = store.restore_archive(archive)
        assert new_sid != "orig-1"
        assert len(new_sid) == 36

        new_data = store.get(new_sid)
        assert new_data is not None
        assert len(new_data.chat_messages) == 2
        assert new_data.chat_messages[0].content == "Hola"
        assert new_data.chat_messages[1].content == "Mundo"

    def test_restore_archive_independent_messages(self, tmp_path):
        """Restoring an archive must give the new session its own message list."""
        from services.archive_service import ArchiveService

        store = SessionStore()
        archive_svc = ArchiveService(tmp_path / "archives")

        from models.session_archive import SessionArchive
        archive = SessionArchive(
            archive_id="restore-indep",
            name="Indep",
            original_session_id="o1",
            archived_at=1000.0,
            message_count=1,
            datasets=[],
            messages=[ChatMessage(role="user", content="Solo")],
            provider="test",
        )
        archive_svc.save_archive(archive)

        # Restore twice — each must have independent messages
        sid_a = store.restore_archive(archive)
        sid_b = store.restore_archive(archive)

        data_a = store.get(sid_a)
        data_b = store.get(sid_b)
        assert data_a is not None
        assert data_b is not None

        data_a.chat_messages.append(ChatMessage(role="assistant", content="Nuevo"))
        assert len(data_b.chat_messages) == 1  # unchanged
