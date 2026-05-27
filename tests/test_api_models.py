"""Tests for api/models/ — Pydantic model validation and serialization."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from api.models.chat import MessageRequest, MessageResponse
from api.models.dashboard import DashboardItem, DashboardResponse
from api.models.errors import ErrorCode, ErrorResponse
from api.models.files import FileMetadata, FilePreview, UploadResponse
from api.models.session import SessionResetResponse, SessionState
from api.models.settings import SettingsRequest, SettingsResponse


# ─── errors ─────────────────────────────────────────────────────────


class TestErrorCode:
    def test_values(self):
        assert ErrorCode.BAD_REQUEST.value == "BAD_REQUEST"
        assert ErrorCode.NOT_FOUND.value == "NOT_FOUND"
        assert ErrorCode.CONFLICT.value == "CONFLICT"
        assert ErrorCode.SERVICE_UNAVAILABLE.value == "SERVICE_UNAVAILABLE"
        assert ErrorCode.SESSION_EXPIRED.value == "SESSION_EXPIRED"

    def test_is_str_enum(self):
        assert isinstance(ErrorCode.BAD_REQUEST, str)


class TestErrorResponse:
    def test_minimal(self):
        resp = ErrorResponse(error="Not found", code=ErrorCode.NOT_FOUND)
        assert resp.error == "Not found"
        assert resp.code == ErrorCode.NOT_FOUND

    def test_serialization_roundtrip(self):
        original = ErrorResponse(error="Bad request", code=ErrorCode.BAD_REQUEST)
        data = original.model_dump()
        restored = ErrorResponse.model_validate(data)
        assert restored == original

    def test_string_code_accepted(self):
        """Pydantic should coerce a plain string into the Enum."""
        resp = ErrorResponse.model_validate({"error": "x", "code": "CONFLICT"})
        assert resp.code == ErrorCode.CONFLICT

    def test_invalid_code_raises(self):
        with pytest.raises(ValidationError):
            ErrorResponse.model_validate({"error": "x", "code": "INVALID_CODE"})


# ─── files ──────────────────────────────────────────────────────────


class TestFileMetadata:
    def test_minimal(self):
        now = datetime(2025, 1, 1)
        fm = FileMetadata(
            filename="data.csv",
            display_name="data.csv",
            size_bytes=100,
            rows=10,
            columns=3,
            loaded_at=now,
        )
        assert fm.filename == "data.csv"
        assert fm.rows == 10
        assert fm.columns == 3

    def test_optional_fields_default(self):
        now = datetime(2025, 1, 1)
        fm = FileMetadata(
            filename="test.csv",
            display_name="test.csv",
            loaded_at=now,
        )
        assert fm.sheet_name == ""
        assert fm.size_bytes == 0
        assert fm.rows == 0
        assert fm.columns == 0
        assert fm.dtypes == {}

    def test_serialization_roundtrip(self):
        now = datetime(2025, 1, 1)
        original = FileMetadata(
            filename="data.csv",
            display_name="Data CSV",
            sheet_name="Sheet1",
            size_bytes=512,
            rows=100,
            columns=5,
            dtypes={"col1": "int64", "col2": "object"},
            loaded_at=now,
        )
        data = original.model_dump()
        restored = FileMetadata.model_validate(data)
        assert restored == original

    def test_filename_required(self):
        with pytest.raises(ValidationError):
            FileMetadata.model_validate({"display_name": "x", "loaded_at": datetime.now()})


class TestFilePreview:
    def test_basic(self):
        fp = FilePreview(filename="data.csv", preview_html="<table></table>")
        assert fp.filename == "data.csv"
        assert fp.preview_html == "<table></table>"

    def test_serialization_roundtrip(self):
        original = FilePreview(filename="data.csv", preview_html="<table><tr><td>1</td></tr></table>")
        data = original.model_dump()
        restored = FilePreview.model_validate(data)
        assert restored == original


class TestUploadResponse:
    def test_basic(self):
        resp = UploadResponse(filename="test.csv", display_name="test.csv", rows=50, columns=4)
        assert resp.message == "Archivo cargado correctamente."

    def test_custom_message(self):
        resp = UploadResponse(
            filename="test.csv",
            display_name="test.csv",
            rows=0,
            columns=0,
            message="Warning: empty file",
        )
        assert resp.message == "Warning: empty file"

    def test_serialization_roundtrip(self):
        original = UploadResponse(filename="f.csv", display_name="F", rows=10, columns=3)
        data = original.model_dump()
        restored = UploadResponse.model_validate(data)
        assert restored == original


# ─── chat ───────────────────────────────────────────────────────────


class TestMessageRequest:
    def test_basic(self):
        req = MessageRequest(message="Hello")
        assert req.message == "Hello"

    def test_message_required(self):
        with pytest.raises(ValidationError):
            MessageRequest.model_validate({})

    def test_serialization_roundtrip(self):
        original = MessageRequest(message="Analyze this data")
        data = original.model_dump()
        restored = MessageRequest.model_validate(data)
        assert restored == original


class TestMessageResponse:
    def test_minimal(self):
        resp = MessageResponse(message_id=1)
        assert resp.message_id == 1
        assert resp.role == "assistant"
        assert resp.content == ""
        assert resp.figure_html is None
        assert resp.dataframe_json is None
        assert resp.error is False

    def test_with_figure(self):
        resp = MessageResponse(
            message_id=2,
            content="Here's a chart",
            figure_html='<div class="plotly-graph-div"></div>',
        )
        assert resp.figure_html is not None
        assert resp.dataframe_json is None

    def test_full_response(self):
        resp = MessageResponse(
            message_id=3,
            role="user",
            content="What's the average?",
            figure_html="<div></div>",
            dataframe_json='{"data": []}',
            error=False,
        )
        assert resp.role == "user"
        assert resp.dataframe_json == '{"data": []}'

    def test_error_response(self):
        resp = MessageResponse(message_id=4, content="Error occurred", error=True)
        assert resp.error is True

    def test_serialization_roundtrip(self):
        original = MessageResponse(
            message_id=5,
            content="Testing",
            figure_html="<div></div>",
        )
        data = original.model_dump()
        restored = MessageResponse.model_validate(data)
        assert restored == original


# ─── dashboard ──────────────────────────────────────────────────────


class TestDashboardItem:
    def test_minimal(self):
        item = DashboardItem(id="1", title="Sales", chart_type="bar")
        assert item.figure_html is None
        assert item.kpi_value is None

    def test_with_values(self):
        item = DashboardItem(
            id="2",
            title="Revenue",
            chart_type="kpi",
            kpi_value="$42,000",
        )
        assert item.kpi_value == "$42,000"

    def test_with_figure_html(self):
        item = DashboardItem(
            id="3",
            title="Chart",
            chart_type="line",
            figure_html='<div class="plotly-graph-div"></div>',
        )
        assert item.figure_html is not None

    def test_serialization_roundtrip(self):
        original = DashboardItem(id="a1", title="Test", chart_type="bar", figure_html="<div></div>")
        data = original.model_dump()
        restored = DashboardItem.model_validate(data)
        assert restored == original


class TestDashboardResponse:
    def test_empty(self):
        resp = DashboardResponse(items=[])
        assert resp.items == []

    def test_with_items(self):
        items = [
            DashboardItem(id="1", title="A", chart_type="bar"),
            DashboardItem(id="2", title="B", chart_type="line"),
        ]
        resp = DashboardResponse(items=items)
        assert len(resp.items) == 2

    def test_serialization_roundtrip(self):
        original = DashboardResponse(
            items=[DashboardItem(id="x", title="X", chart_type="kpi", kpi_value="10")]
        )
        data = original.model_dump()
        restored = DashboardResponse.model_validate(data)
        assert restored == original


# ─── settings ───────────────────────────────────────────────────────


class TestSettingsRequest:
    def test_empty(self):
        req = SettingsRequest()
        assert req.api_key is None
        assert req.model is None

    def test_with_values(self):
        req = SettingsRequest(api_key="sk-123", model="gemini-2.0")
        assert req.api_key == "sk-123"
        assert req.model == "gemini-2.0"

    def test_serialization_roundtrip(self):
        original = SettingsRequest(api_key="sk-test", model="gemini-2.5-flash")
        data = original.model_dump()
        restored = SettingsRequest.model_validate(data)
        assert restored == original


class TestSettingsResponse:
    def test_basic(self):
        resp = SettingsResponse(
            model="gemini-2.5-flash",
            provider="Gemini (gemini-2.5-flash)",
            is_configured=True,
        )
        assert resp.is_configured is True

    def test_not_configured(self):
        resp = SettingsResponse(
            model="gemini-2.5-flash",
            provider="Gemini (gemini-2.5-flash)",
            is_configured=False,
        )
        assert resp.is_configured is False

    def test_serialization_roundtrip(self):
        original = SettingsResponse(
            model="test-model",
            provider="Test provider",
            is_configured=True,
        )
        data = original.model_dump()
        restored = SettingsResponse.model_validate(data)
        assert restored == original


# ─── session ────────────────────────────────────────────────────────


class TestSessionState:
    def test_basic(self):
        state = SessionState(
            session_id="abc-123",
            file_count=2,
            files=["a.csv", "b.csv"],
            message_count=5,
            provider="Gemini (gemini-2.5-flash)",
        )
        assert state.file_count == 2
        assert state.message_count == 5
        assert "a.csv" in state.files

    def test_empty_session(self):
        state = SessionState(
            session_id="xyz",
            file_count=0,
            files=[],
            message_count=0,
            provider="",
        )
        assert state.file_count == 0
        assert state.files == []

    def test_serialization_roundtrip(self):
        original = SessionState(
            session_id="sid-1",
            file_count=1,
            files=["data.csv"],
            message_count=3,
            provider="Gemini",
        )
        data = original.model_dump()
        restored = SessionState.model_validate(data)
        assert restored == original


class TestSessionResetResponse:
    def test_basic(self):
        resp = SessionResetResponse(old_session="old-123", new_session="new-456")
        assert resp.old_session == "old-123"
        assert resp.new_session == "new-456"

    def test_serialization_roundtrip(self):
        original = SessionResetResponse(old_session="aaa", new_session="bbb")
        data = original.model_dump()
        restored = SessionResetResponse.model_validate(data)
        assert restored == original
