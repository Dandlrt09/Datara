"""Integration test: upload → archive → reset → restore → verify file persists."""

from __future__ import annotations

import csv
import io
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers import api_router
from api.session_data import SessionData
from api.session_store import SessionStore
from services.archive_service import ArchiveService


@pytest.fixture
def store() -> SessionStore:
    return SessionStore(ttl=3600)


@pytest.fixture
def uploads_dir(tmp_path: Path) -> Path:
    return tmp_path / "uploads"


@pytest.fixture
def client(
    tmp_path: Path,
    store: SessionStore,
    uploads_dir: Path,
) -> Generator[TestClient, None, None]:
    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        app.state.store = store
        app.state.archive_service = ArchiveService(tmp_path / "archives")
        uploads_dir.mkdir(parents=True, exist_ok=True)
        app.state.uploads_dir = uploads_dir
        yield

    app = FastAPI(lifespan=_lifespan)
    app.include_router(api_router)

    with TestClient(app) as c:
        yield c


def _make_csv_bytes(filename: str = "test.csv", rows: int = 10) -> tuple[str, bytes]:
    """Create a simple CSV file in memory and return (filename, bytes)."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "name", "value"])
    for i in range(rows):
        writer.writerow([i, f"item_{i}", i * 10])
    return filename, buf.getvalue().encode("utf-8")


class TestFilePersistenceFullCycle:
    """Upload → archive → restore — files must survive."""

    def test_upload_archive_restore_file_persists(self, client: TestClient, uploads_dir: Path):
        # ── Step 1: Create a fresh session ─────────────────────────
        resp = client.post("/api/session/reset")
        assert resp.status_code == 200
        sid = resp.json()["new_session"]

        # ── Step 2: Upload a file ──────────────────────────────────
        filename, content = _make_csv_bytes("computers.csv")
        resp = client.post(
            "/api/files/upload",
            files={"file": (filename, content, "text/csv")},
            headers={"X-Session-Id": sid},
        )
        assert resp.status_code == 201, f"Upload failed: {resp.text}"
        assert resp.json()["filename"] == filename

        # Verify file saved to disk
        disk_path = uploads_dir / sid / filename
        assert disk_path.exists(), f"File not saved to disk at {disk_path}"

        # Verify file is in session
        resp = client.get("/api/files", headers={"X-Session-Id": sid})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        # ── Step 3: Archive the session ────────────────────────────
        resp = client.post(
            "/api/session/current/archive",
            json={},
            headers={"X-Session-Id": sid},
        )
        assert resp.status_code == 200, f"Archive failed: {resp.text}"
        archive_id = resp.json()["archive_id"]

        # ── Step 4: Reset session (simulates what frontend does) ───
        resp = client.post("/api/session/reset", headers={"X-Session-Id": sid})
        assert resp.status_code == 200
        new_sid = resp.json()["new_session"]

        # Verify new session has no files
        resp = client.get("/api/files", headers={"X-Session-Id": new_sid})
        assert resp.status_code == 200
        assert len(resp.json()) == 0

        # ── Step 5: Restore the archive ────────────────────────────
        resp = client.post(f"/api/session/archived/{archive_id}/restore")
        assert resp.status_code == 200, f"Restore failed: {resp.text}"
        restore_data = resp.json()

        restored_sid = restore_data["new_session_id"]
        assert restore_data["datasets"][0]["needed"] == False, \
            f"File should be 'restored' (needed=false), got: {restore_data['datasets']}"

        # ── Step 6: Verify file is in the restored session ─────────
        resp = client.get("/api/files", headers={"X-Session-Id": restored_sid})
        assert resp.status_code == 200
        files = resp.json()
        assert len(files) == 1, f"Expected 1 file, got {len(files)}: {files}"
        assert files[0]["filename"] == filename
        assert files[0]["display_name"] == filename

    def test_upload_archive_restore_without_disk_file_shows_needed(self, client: TestClient, uploads_dir: Path):
        """If the disk file was deleted, restore should return needed=True."""
        resp = client.post("/api/session/reset")
        sid = resp.json()["new_session"]

        filename, content = _make_csv_bytes("missing.csv")
        resp = client.post(
            "/api/files/upload",
            files={"file": (filename, content, "text/csv")},
            headers={"X-Session-Id": sid},
        )
        assert resp.status_code == 201

        resp = client.post(
            "/api/session/current/archive",
            json={},
            headers={"X-Session-Id": sid},
        )
        archive_id = resp.json()["archive_id"]

        # Delete the file from disk to simulate disk loss
        disk_path = uploads_dir / sid / filename
        assert disk_path.exists()
        disk_path.unlink()

        resp = client.post(f"/api/session/archived/{archive_id}/restore")
        assert resp.status_code == 200
        restore_data = resp.json()
        assert restore_data["datasets"][0]["needed"] == True, \
            "File deleted from disk should report needed=True"

