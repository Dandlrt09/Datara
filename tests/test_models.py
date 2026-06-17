"""Tests for models/ — FileData, ChatMessage, AnalysisResult."""

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go

from models.file_data import FileData
from models.chat_message import ChatMessage
from models.analysis_result import AnalysisResult


class TestFileData:
    """FileData dataclass with computed fields."""

    def test_basic_creation(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4.0, 5.0, 6.0]})
        fd = FileData(filename="test.csv", df=df, size_bytes=100)

        assert fd.filename == "test.csv"
        assert fd.display_name == "test.csv"
        assert fd.rows == 3
        assert fd.columns == 2
        assert fd.size_bytes == 100
        assert fd.sheet_name == ""
        assert isinstance(fd.loaded_at, datetime)

    def test_display_name_override(self):
        df = pd.DataFrame({"x": [1]})
        fd = FileData(filename="test.csv", df=df, display_name="Custom Name")
        assert fd.display_name == "Custom Name"

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        fd = FileData(filename="empty.csv", df=df)
        assert fd.rows == 0
        assert fd.columns == 0
        assert fd.dtypes == {}

    def test_dtypes_populated(self):
        df = pd.DataFrame({
            "texto": ["a", "b"],
            "numero": [1, 2],
            "decimal": [1.5, 2.5],
        })
        fd = FileData(filename="tipos.csv", df=df)
        assert fd.dtypes["texto"] == "object"
        assert fd.dtypes["numero"] == "int64"
        assert fd.dtypes["decimal"] == "float64"

    def test_summary_includes_filename_rows_columns(self):
        df = pd.DataFrame({"name": ["Alice", "Bob"], "age": [30, 25]})
        fd = FileData(filename="people.csv", df=df)

        summary = fd.summary()
        assert "people.csv" in summary
        assert "Filas: 2" in summary
        assert "Columnas: 2" in summary
        assert "name" in summary
        assert "age" in summary

    def test_summary_contains_head(self):
        df = pd.DataFrame({"x": range(10)})
        fd = FileData(filename="range.csv", df=df)

        summary = fd.summary()
        assert "Primeras 5 filas" in summary

    def test_is_empty_true(self):
        fd = FileData(filename="empty.csv", df=pd.DataFrame())
        assert fd.is_empty is True

    def test_is_empty_false(self):
        fd = FileData(filename="not_empty.csv", df=pd.DataFrame({"a": [1]}))
        assert fd.is_empty is False


class TestChatMessage:
    """ChatMessage dataclass with export formatting."""

    def test_user_message(self):
        msg = ChatMessage(role="user", content="¿cuál es el promedio?")
        assert msg.role == "user"
        assert msg.content == "¿cuál es el promedio?"
        assert msg.error is False
        assert msg.figure_json is None
        assert msg.dataframe_json is None

    def test_assistant_message(self):
        msg = ChatMessage(
            role="assistant",
            content="El promedio es 42.",
            figure_json='{"data": []}',
        )
        assert msg.role == "assistant"

    def test_to_export_text_user(self):
        msg = ChatMessage(role="user", content="Hola")
        text = msg.to_export_text(1)
        assert "[1] Tú:" in text
        assert "Hola" in text

    def test_to_export_text_assistant(self):
        msg = ChatMessage(role="assistant", content="Respuesta")
        text = msg.to_export_text(2)
        assert "[2] Asistente:" in text
        assert "Respuesta" in text

    def test_to_export_text_with_figure(self):
        msg = ChatMessage(
            role="assistant",
            content="Gráfico generado",
            figure_json='{"data": []}',
        )
        text = msg.to_export_text(1)
        assert "[Gráfico generado]" in text

    def test_to_export_text_with_dataframe(self):
        df = pd.DataFrame({"x": [1], "y": [2]})
        msg = ChatMessage(
            role="assistant",
            content="Tabla generada",
            dataframe_json=df.to_json(orient="split"),
        )
        text = msg.to_export_text(1)
        assert "[Tabla de datos generada]" in text

    def test_to_export_text_with_both_figure_and_dataframe(self):
        msg = ChatMessage(
            role="assistant",
            content="Ambos",
            figure_json="{}",
            dataframe_json="{}",
        )
        text = msg.to_export_text(1)
        assert "[Gráfico generado]" in text
        assert "[Tabla de datos generada]" in text

    def test_to_export_text_error_message(self):
        msg = ChatMessage(role="assistant", content="Error", error=True)
        text = msg.to_export_text(1)
        assert "Asistente" in text

    def test_timestamp_auto_generated(self):
        msg = ChatMessage(role="user", content="test")
        assert isinstance(msg.timestamp, datetime)


class TestAnalysisResult:
    """AnalysisResult dataclass with computed properties."""

    def test_default_success(self):
        result = AnalysisResult()
        assert result.success is True
        assert result.text == ""
        assert result.figure is None
        assert result.dataframe is None
        assert result.error is None
        assert result.code_executed == ""

    def test_success_with_error(self):
        result = AnalysisResult(text="Algo salió mal", error="Error en sandbox")
        assert result.success is False

    def test_has_figure_true(self):
        result = AnalysisResult(figure=go.Figure())
        assert result.has_figure is True

    def test_has_figure_false(self):
        result = AnalysisResult()
        assert result.has_figure is False

    def test_has_dataframe_true(self):
        result = AnalysisResult(dataframe=pd.DataFrame({"a": [1]}))
        assert result.has_dataframe is True

    def test_has_dataframe_false(self):
        result = AnalysisResult()
        assert result.has_dataframe is False

    def test_success_with_text_only(self):
        result = AnalysisResult(text="Todo bien")
        assert result.success is True
        assert result.text == "Todo bien"
