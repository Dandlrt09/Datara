"""Integration tests for all API routers.

Tests exercise the real dependency chain (FastAPI + routers + store)
with a ``TestClient``.  Services (``FileService``, ``CodeExecutor``)
are either exercised with real lightweight data or mocked for
code paths that would require an LLM call.

Every test sends ``X-Session-Id: test-session-uuid-1234`` (from the
conftest fixture) unless the endpoint under test intentionally omits it.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, PropertyMock

import pandas as pd
import plotly.graph_objects as go
import pytest
from fastapi.testclient import TestClient

from api.models import ErrorCode
from models import AnalysisResult, ChatMessage

# ─────────────────────────────────────────────────────────────────────
# Session router
# ─────────────────────────────────────────────────────────────────────


class TestSessionRouter:
    """GET /api/session  •  POST /api/session/reset"""

    def test_get_session_state(self, client: TestClient, session_id: str):
        resp = client.get("/api/session", headers={"X-Session-Id": session_id})
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == session_id
        assert data["file_count"] == 0
        assert data["files"] == []
        assert data["message_count"] == 0

    def test_get_session_missing_header_returns_400(self, client: TestClient):
        resp = client.get("/api/session")
        assert resp.status_code == 400

    def test_get_session_unknown_id_returns_404(self, client: TestClient):
        resp = client.get(
            "/api/session",
            headers={"X-Session-Id": "i-do-not-exist"},
        )
        assert resp.status_code == 404

    def test_reset_session_creates_new(self, client: TestClient):
        resp = client.post("/api/session/reset")
        assert resp.status_code == 200
        data = resp.json()
        assert data["old_session"] == ""  # no header sent
        assert len(data["new_session"]) == 36  # UUID v4
        assert data["new_session"].count("-") == 4

    def test_reset_session_echoes_old_id(self, client: TestClient, session_id: str):
        resp = client.post(
            "/api/session/reset",
            headers={"X-Session-Id": session_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["old_session"] == session_id
        assert data["new_session"] != session_id

    def test_reset_session_old_still_accessible(self, client: TestClient, session_id: str):
        """The old session is NOT invalidated on reset."""
        client.post(
            "/api/session/reset",
            headers={"X-Session-Id": session_id},
        )
        resp = client.get("/api/session", headers={"X-Session-Id": session_id})
        assert resp.status_code == 200  # old session still alive


# ─────────────────────────────────────────────────────────────────────
# Files router
# ─────────────────────────────────────────────────────────────────────


class TestFilesRouter:
    """POST /api/files/upload  •  GET /api/files  •  DELETE /api/files/{fn}  •  GET .../preview"""

    CSV_SAMPLE = b"col1,col2\n1,2\n3,4\n5,6"

    def test_upload_and_list(self, client: TestClient, session_id: str):
        # Upload
        resp = client.post(
            "/api/files/upload",
            files={"file": ("test.csv", self.CSV_SAMPLE, "text/csv")},
            headers={"X-Session-Id": session_id},
        )
        assert resp.status_code == 201
        meta = resp.json()
        assert meta["filename"] == "test.csv"
        assert meta["rows"] == 3
        assert meta["columns"] == 2

        # List
        resp = client.get("/api/files", headers={"X-Session-Id": session_id})
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        assert items[0]["filename"] == "test.csv"

    def test_upload_duplicate_returns_409(self, client: TestClient, session_id: str):
        client.post(
            "/api/files/upload",
            files={"file": ("dup.csv", b"a,b\n1,2", "text/csv")},
            headers={"X-Session-Id": session_id},
        )
        resp = client.post(
            "/api/files/upload",
            files={"file": ("dup.csv", b"a,b\n3,4", "text/csv")},
            headers={"X-Session-Id": session_id},
        )
        assert resp.status_code == 409
        # FastAPI wraps HTTPException.detail under a ``detail`` key
        assert resp.json()["detail"]["code"] == ErrorCode.CONFLICT.value

    def test_upload_replace(self, client: TestClient, session_id: str):
        client.post(
            "/api/files/upload",
            files={"file": ("rep.csv", b"a,b\n1,2", "text/csv")},
            headers={"X-Session-Id": session_id},
        )
        resp = client.post(
            "/api/files/upload?replace=true",
            files={"file": ("rep.csv", b"a,b\n3,4,5", "text/csv")},
            headers={"X-Session-Id": session_id},
        )
        assert resp.status_code == 201
        assert resp.json()["filename"] == "rep.csv"

    def test_upload_invalid_type_returns_400(self, client: TestClient, session_id: str):
        resp = client.post(
            "/api/files/upload",
            files={"file": ("bad.pdf", b"%PDF-1.4...", "application/pdf")},
            headers={"X-Session-Id": session_id},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == ErrorCode.BAD_REQUEST.value

    def test_upload_empty_file_returns_400(self, client: TestClient, session_id: str):
        resp = client.post(
            "/api/files/upload",
            files={"file": ("empty.csv", b"", "text/csv")},
            headers={"X-Session-Id": session_id},
        )
        assert resp.status_code == 400

    def test_delete_existing_file(self, client: TestClient, session_id: str):
        client.post(
            "/api/files/upload",
            files={"file": ("del.csv", self.CSV_SAMPLE, "text/csv")},
            headers={"X-Session-Id": session_id},
        )
        resp = client.delete("/api/files/del.csv", headers={"X-Session-Id": session_id})
        assert resp.status_code == 204

        # Verify gone
        resp = client.get("/api/files", headers={"X-Session-Id": session_id})
        assert len(resp.json()) == 0

    def test_delete_nonexistent_returns_404(self, client: TestClient, session_id: str):
        resp = client.delete(
            "/api/files/nope.csv",
            headers={"X-Session-Id": session_id},
        )
        assert resp.status_code == 404

    def test_preview_file(self, client: TestClient, session_id: str):
        client.post(
            "/api/files/upload",
            files={"file": ("prev.csv", self.CSV_SAMPLE, "text/csv")},
            headers={"X-Session-Id": session_id},
        )
        resp = client.get(
            "/api/files/prev.csv/preview?rows=2",
            headers={"X-Session-Id": session_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] == "prev.csv"
        assert data["columns"] == ["col1", "col2"]
        assert data["total_rows"] == 3
        assert len(data["preview"]) == 2

    def test_preview_nonexistent_returns_404(self, client: TestClient, session_id: str):
        resp = client.get(
            "/api/files/missing.csv/preview",
            headers={"X-Session-Id": session_id},
        )
        assert resp.status_code == 404

    def test_preview_rows_max_100(self, client: TestClient, session_id: str):
        """Query parameter ``rows`` is capped at 100."""
        client.post(
            "/api/files/upload",
            files={"file": ("r.csv", self.CSV_SAMPLE, "text/csv")},
            headers={"X-Session-Id": session_id},
        )
        # Returns 422 because `rows` param has le=100 constraint
        resp = client.get(
            "/api/files/r.csv/preview?rows=999",
            headers={"X-Session-Id": session_id},
        )
        assert resp.status_code == 422

    def test_upload_no_session_returns_400(self, client: TestClient):
        resp = client.post(
            "/api/files/upload",
            files={"file": ("x.csv", b"a\n1", "text/csv")},
        )
        assert resp.status_code == 400


# ─────────────────────────────────────────────────────────────────────
# Chat router
# ─────────────────────────────────────────────────────────────────────


class TestChatRouter:
    """POST /api/chat/message  •  GET /api/chat/history  •  DELETE /api/chat/clear"""

    def test_send_message_no_llm_returns_error(self, client: TestClient, session_id: str):
        """LLM is not configured → returns error=true.

        CodeExecutor checks for files **before** checking the API key,
        so we upload a small file first to get past the "no files" guard.
        """
        client.post(
            "/api/files/upload",
            files={"file": ("data.csv", b"x,y\n1,2", "text/csv")},
            headers={"X-Session-Id": session_id},
        )
        resp = client.post(
            "/api/chat/message",
            json={"message": "¿Cuál es el promedio?"},
            headers={"X-Session-Id": session_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["error"] is True
        assert "API key" in data["content"]

    def test_send_empty_message_returns_400(self, client: TestClient, session_id: str):
        resp = client.post(
            "/api/chat/message",
            json={"message": "   "},
            headers={"X-Session-Id": session_id},
        )
        assert resp.status_code == 400

    def test_send_message_with_mock_analysis(self, client: TestClient, session_id: str, session_data):
        """Mock CodeExecutor.analyze to return a known AnalysisResult.

        We also set a fake API key so the ``is_configured`` guard
        passes and the mock is actually exercised.
        """
        session_data.llm_service.api_key = "test-key-for-mock"
        mock_result = AnalysisResult(
            text="El promedio es 42.",
            figure=go.Figure(),
            dataframe=pd.DataFrame({"x": [1, 2]}),
        )
        session_data.code_executor.analyze = MagicMock(return_value=mock_result)

        resp = client.post(
            "/api/chat/message",
            json={"message": "¿Cuál es el promedio?"},
            headers={"X-Session-Id": session_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "assistant"
        assert "42" in data["content"]
        assert data["figure_html"] is not None  # exported as HTML
        assert data["dataframe_json"] is not None
        assert data["error"] is False

    def test_get_history_empty(self, client: TestClient, session_id: str):
        resp = client.get("/api/chat/history", headers={"X-Session-Id": session_id})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_history_after_message(self, client: TestClient, session_id: str, session_data):
        """After sending a message, history contains user + assistant messages."""
        session_data.llm_service.api_key = "test-key-for-mock"
        session_data.code_executor.analyze = MagicMock(
            return_value=AnalysisResult(text="42"),
        )
        # Send one message
        client.post(
            "/api/chat/message",
            json={"message": "dame el promedio"},
            headers={"X-Session-Id": session_id},
        )
        # History should have 2 entries (user + assistant)
        resp = client.get("/api/chat/history", headers={"X-Session-Id": session_id})
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 2
        assert items[0]["role"] == "user"
        assert items[1]["role"] == "assistant"

    def test_clear_chat(self, client: TestClient, session_id: str):
        # Pre-populate a message
        session_data = client.app.state.store.get(session_id)
        session_data.chat_messages.append(
            ChatMessage(role="user", content="test"),
        )

        resp = client.delete("/api/chat/clear", headers={"X-Session-Id": session_id})
        assert resp.status_code == 204

        resp = client.get("/api/chat/history", headers={"X-Session-Id": session_id})
        assert resp.json() == []


# ─────────────────────────────────────────────────────────────────────
# Dashboard router
# ─────────────────────────────────────────────────────────────────────


class TestDashboardRouter:
    """GET /api/dashboard  •  POST /api/dashboard  •  DELETE /api/dashboard/{id}"""

    def test_get_dashboard_empty(self, client: TestClient, session_id: str):
        resp = client.get("/api/dashboard", headers={"X-Session-Id": session_id})
        assert resp.status_code == 200
        assert resp.json() == {"items": []}

    def test_add_and_list_item(self, client: TestClient, session_id: str):
        body = {
            "file": "data.csv",
            "title": "Ventas por mes",
            "chart_type": "line",
            "config": {"x": "Mes", "y": "Ventas"},
        }
        resp = client.post(
            "/api/dashboard",
            json=body,
            headers={"X-Session-Id": session_id},
        )
        assert resp.status_code == 201
        item = resp.json()
        assert item["title"] == "Ventas por mes"
        assert item["chart_type"] == "line"
        assert item["id"].startswith("item_")

        # List
        resp = client.get("/api/dashboard", headers={"X-Session-Id": session_id})
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["id"] == item["id"]

    def test_get_dashboard_with_filter(self, client: TestClient, session_id: str):
        client.post(
            "/api/dashboard",
            json={"file": "d.csv", "title": "KPI1", "chart_type": "kpi", "config": {}},
            headers={"X-Session-Id": session_id},
        )
        resp = client.get(
            "/api/dashboard?filter_col=Region&filter_vals=Norte,Sur",
            headers={"X-Session-Id": session_id},
        )
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1

    def test_delete_item(self, client: TestClient, session_id: str):
        # Add
        resp = client.post(
            "/api/dashboard",
            json={"title": "DelMe", "chart_type": "kpi", "config": {}},
            headers={"X-Session-Id": session_id},
        )
        item_id = resp.json()["id"]

        # Delete
        resp = client.delete(
            f"/api/dashboard/{item_id}",
            headers={"X-Session-Id": session_id},
        )
        assert resp.status_code == 204

        # Verify gone
        resp = client.get("/api/dashboard", headers={"X-Session-Id": session_id})
        assert resp.json()["items"] == []

    def test_delete_nonexistent_returns_404(self, client: TestClient, session_id: str):
        resp = client.delete(
            "/api/dashboard/nonexistent-id",
            headers={"X-Session-Id": session_id},
        )
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────
# Settings router
# ─────────────────────────────────────────────────────────────────────


class TestSettingsRouter:
    """GET /api/settings  •  PUT /api/settings"""

    def test_get_settings_defaults(self, client: TestClient, session_id: str):
        resp = client.get("/api/settings", headers={"X-Session-Id": session_id})
        assert resp.status_code == 200
        data = resp.json()
        assert data["model"] == "models/gemini-test"
        assert data["is_configured"] is False

    def test_update_api_key(self, client: TestClient, session_id: str):
        resp = client.put(
            "/api/settings",
            json={"api_key": "AIzaSyAtest", "model": "models/gemini-2.0-flash"},
            headers={"X-Session-Id": session_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["model"] == "models/gemini-2.0-flash"
        assert data["is_configured"] is True

    def test_update_partial(self, client: TestClient, session_id: str):
        """Only ``model`` changes, ``api_key`` stays as-is."""
        client.put(
            "/api/settings",
            json={"api_key": "AIzaSyAtest", "model": "models/gemini-2.0-flash"},
            headers={"X-Session-Id": session_id},
        )
        resp = client.put(
            "/api/settings",
            json={"model": "models/gemini-2.5-flash"},
            headers={"X-Session-Id": session_id},
        )
        assert resp.status_code == 200
        assert resp.json()["model"] == "models/gemini-2.5-flash"

    def test_update_triggers_code_executor_rebuild(self, client: TestClient, session_id: str):
        """Changing settings replaces the session's CodeExecutor."""
        session_data = client.app.state.store.get(session_id)
        old_exec = id(session_data.code_executor)

        client.put(
            "/api/settings",
            json={"api_key": "AIzaSyAtest"},
            headers={"X-Session-Id": session_id},
        )

        new_exec = id(session_data.code_executor)
        assert new_exec != old_exec


# ─────────────────────────────────────────────────────────────────────
# Export router
# ─────────────────────────────────────────────────────────────────────


class TestExportRouter:
    """GET /api/export/{mid}/chart  •  GET /api/export/{mid}/data  •  GET /api/export/session"""

    def _seed_chat(self, session_data):
        """Add a user + assistant message pair with figure & dataframe."""
        session_data.chat_messages.append(
            ChatMessage(role="user", content="show chart"),
        )
        session_data.chat_messages.append(
            ChatMessage(
                role="assistant",
                content="Here is your chart",
                figure_json='<div class="plotly-graph-div"></div>',
                dataframe_json=pd.DataFrame({"a": [1, 2]}).to_json(orient="split"),
            ),
        )

    def test_export_chart_html(self, client: TestClient, session_id: str, session_data):
        self._seed_chat(session_data)

        resp = client.get("/api/export/1/chart", headers={"X-Session-Id": session_id})
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/html; charset=utf-8"
        assert "plotly-graph-div" in resp.text

    def test_export_chart_no_figure_returns_404(self, client: TestClient, session_id: str, session_data):
        session_data.chat_messages.append(
            ChatMessage(role="user", content="hi"),
        )
        session_data.chat_messages.append(
            ChatMessage(role="assistant", content="no figure here"),
        )
        resp = client.get("/api/export/1/chart", headers={"X-Session-Id": session_id})
        assert resp.status_code == 404

    def test_export_chart_nonexistent_message_returns_404(self, client: TestClient, session_id: str):
        resp = client.get("/api/export/999/chart", headers={"X-Session-Id": session_id})
        assert resp.status_code == 404

    def test_export_data_csv(self, client: TestClient, session_id: str, session_data):
        self._seed_chat(session_data)

        resp = client.get("/api/export/1/data", headers={"X-Session-Id": session_id})
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/csv; charset=utf-8"
        assert "a" in resp.text  # column header

    def test_export_data_no_df_returns_404(self, client: TestClient, session_id: str, session_data):
        session_data.chat_messages.append(
            ChatMessage(role="assistant", content="no data"),
        )
        resp = client.get("/api/export/0/data", headers={"X-Session-Id": session_id})
        assert resp.status_code == 404

    def test_export_session_text(self, client: TestClient, session_id: str, session_data):
        session_data.chat_messages.append(
            ChatMessage(role="user", content="hola"),
        )
        session_data.chat_messages.append(
            ChatMessage(role="assistant", content="mundo"),
        )

        resp = client.get("/api/export/session", headers={"X-Session-Id": session_id})
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/plain; charset=utf-8"
        assert "hola" in resp.text
        assert "mundo" in resp.text


# ─────────────────────────────────────────────────────────────────────
# Archive router
# ─────────────────────────────────────────────────────────────────────


class TestArchiveRouter:
    """All 6 archive endpoints via TestClient."""

    def _seed_archive(self, client: TestClient, archive_id: str, name: str) -> dict:
        """Create an archive by posting to current/archive with a seeded session.

        Returns the archive data that would be returned from the endpoint.
        """
        from datetime import datetime
        from api.session_store import SessionStore
        store: SessionStore = client.app.state.store
        sid = store.create()
        data = store.get(sid)
        data.chat_messages.append(ChatMessage(role="user", content="Hola"))
        data.chat_messages.append(ChatMessage(role="assistant", content="Mundo"))

        resp = client.post(
            "/api/session/current/archive",
            json={},
            headers={"X-Session-Id": sid},
        )
        assert resp.status_code == 200
        return resp.json()

    # ── GET /api/session/archived ──────────────────────────────────

    def test_list_empty(self, client: TestClient):
        resp = client.get("/api/session/archived")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_with_archives(self, client: TestClient):
        a1 = self._seed_archive(client, "a1", "Sesión 1")
        import time
        time.sleep(0.01)  # ensure different timestamps
        a2 = self._seed_archive(client, "a2", "Sesión 2")

        resp = client.get("/api/session/archived")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        # Newest first
        assert data[0]["archive_id"] == a2["archive_id"]
        assert data[1]["archive_id"] == a1["archive_id"]
        for entry in data:
            assert "archive_id" in entry
            assert "name" in entry
            assert "archived_at" in entry
            assert "message_count" in entry
            assert "datasets" in entry

    # ── GET /api/session/archived/{id} ─────────────────────────────

    def test_get_archive_detail(self, client: TestClient):
        created = self._seed_archive(client, "detail-1", "Detail Test")

        resp = client.get(f"/api/session/archived/{created['archive_id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["archive_id"] == created["archive_id"]
        assert data["name"] == created["name"]
        assert "original_session_id" in data
        assert data["message_count"] == 2
        assert "datasets" in data
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][0]["content"] == "Hola"
        assert data["messages"][1]["role"] == "assistant"
        assert "provider" in data

    def test_get_archive_unknown_returns_404(self, client: TestClient):
        resp = client.get("/api/session/archived/i-dont-exist")
        assert resp.status_code == 404

    # ── POST /api/session/current/archive ──────────────────────────

    def test_archive_current_session(self, client: TestClient):
        from api.session_store import SessionStore
        store: SessionStore = client.app.state.store
        sid = store.create()
        data = store.get(sid)
        data.chat_messages.append(ChatMessage(role="user", content="Test"))

        resp = client.post(
            "/api/session/current/archive",
            headers={"X-Session-Id": sid},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "archive_id" in body
        assert body["archive_id"].startswith("archive_")
        assert "name" in body
        assert "archived_at" in body

    def test_archive_empty_session_returns_409(self, client: TestClient):
        from api.session_store import SessionStore
        store: SessionStore = client.app.state.store
        sid = store.create()  # no messages, no files

        resp = client.post(
            "/api/session/current/archive",
            headers={"X-Session-Id": sid},
        )
        assert resp.status_code == 409

    def test_archive_missing_header_returns_400(self, client: TestClient):
        resp = client.post("/api/session/current/archive")
        assert resp.status_code == 400

    def test_archive_nonexistent_session_returns_404(self, client: TestClient):
        resp = client.post(
            "/api/session/current/archive",
            headers={"X-Session-Id": "no-such-session"},
        )
        assert resp.status_code == 404

    # ── POST /api/session/archived/{id}/restore ────────────────────

    def test_restore_archive(self, client: TestClient):
        created = self._seed_archive(client, "restore-1", "Restore Test")

        resp = client.post(f"/api/session/archived/{created['archive_id']}/restore")
        assert resp.status_code == 200
        body = resp.json()
        assert "new_session_id" in body
        assert len(body["new_session_id"]) == 36
        assert body["archive_name"] == created["name"]
        assert "datasets" in body
        assert "messages" in body
        assert len(body["messages"]) == 2

        # Verify messages loaded into new session
        new_sid = body["new_session_id"]
        from api.session_store import SessionStore
        store: SessionStore = client.app.state.store
        new_data = store.get(new_sid)
        assert new_data is not None
        assert len(new_data.chat_messages) == 2

    def test_restore_unknown_archive_returns_404(self, client: TestClient):
        resp = client.post("/api/session/archived/no-such-archive/restore")
        assert resp.status_code == 404

    # ── DELETE /api/session/archived/{id} ──────────────────────────

    def test_delete_archive(self, client: TestClient):
        created = self._seed_archive(client, "delete-1", "Delete Me")

        resp = client.delete(f"/api/session/archived/{created['archive_id']}")
        assert resp.status_code == 204

        # Verify gone
        resp = client.get(f"/api/session/archived/{created['archive_id']}")
        assert resp.status_code == 404

    def test_delete_unknown_archive_returns_404(self, client: TestClient):
        resp = client.delete("/api/session/archived/ghost")
        assert resp.status_code == 404

    # ── PATCH /api/session/archived/{id} ───────────────────────────

    def test_rename_archive(self, client: TestClient):
        created = self._seed_archive(client, "rename-1", "Sesión 1")

        new_name = "Mi análisis final"
        resp = client.patch(
            f"/api/session/archived/{created['archive_id']}",
            json={"name": new_name},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == new_name
        assert data["archive_id"] == created["archive_id"]

        # Verify persisted
        resp = client.get(f"/api/session/archived/{created['archive_id']}")
        assert resp.json()["name"] == new_name

    def test_rename_unknown_archive_returns_404(self, client: TestClient):
        resp = client.patch(
            "/api/session/archived/ghost",
            json={"name": "New name"},
        )
        assert resp.status_code == 404

    # ── AUTO-ARCHIVE ON RESET ──────────────────────────────────────

    def test_reset_auto_archives_non_empty_session(self, client: TestClient):
        """Reset with messages should auto-archive and return archive info."""
        from api.session_store import SessionStore
        store: SessionStore = client.app.state.store
        sid = store.create()
        data = store.get(sid)
        data.chat_messages.append(ChatMessage(role="user", content="Test msg"))

        resp = client.post(
            "/api/session/reset",
            headers={"X-Session-Id": sid},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "new_session" in body
        assert body["old_session"] == sid
        assert body["archived"] is not None
        assert body["archived"]["archive_id"].startswith("archive_")
        assert "name" in body["archived"]
        assert "archived_at" in body["archived"]

    def test_reset_empty_session_no_archive(self, client: TestClient):
        """Reset without messages — no archive created."""
        from api.session_store import SessionStore
        store: SessionStore = client.app.state.store
        sid = store.create()  # no messages

        resp = client.post(
            "/api/session/reset",
            headers={"X-Session-Id": sid},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["archived"] is None

    def test_reset_without_header_no_archive(self, client: TestClient):
        """Reset without X-Session-Id should not try to archive."""
        resp = client.post("/api/session/reset")
        assert resp.status_code == 200
        body = resp.json()
        assert body["archived"] is None
        assert body["old_session"] == ""


# ─────────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────────


class TestHealth:
    """GET /health — no auth required."""

    def test_health(self, client: TestClient):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
