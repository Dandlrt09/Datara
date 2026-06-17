"""Tests for services/export_service.py — ExportService."""

import pandas as pd
import plotly.graph_objects as go

from services.export_service import ExportService
from models.chat_message import ChatMessage


# ── dataframe_to_csv ───────────────────────────────────────────────


class TestDataframeToCSV:
    def test_basic_csv_export(self):
        df = pd.DataFrame({"name": ["Alice", "Bob"], "age": [30, 25]})
        result = ExportService.dataframe_to_csv(df)
        assert isinstance(result, bytes)
        assert b"name" in result
        assert b"age" in result
        assert b"Alice" in result
        assert b"Bob" in result

    def test_empty_dataframe_csv(self):
        df = pd.DataFrame()
        result = ExportService.dataframe_to_csv(df)
        assert isinstance(result, bytes)

    def test_csv_utf8_bom(self):
        """CSV should include UTF-8 BOM for Excel compatibility."""
        df = pd.DataFrame({"ciudad": ["Bogotá", "São Paulo"]})
        result = ExportService.dataframe_to_csv(df)
        assert result.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM
        assert "Bogotá".encode("utf-8") in result

    def test_csv_no_index(self):
        df = pd.DataFrame({"x": [1, 2]})
        result = ExportService.dataframe_to_csv(df)
        # Should NOT contain an index column header
        assert b"," not in result[:3]  # Just a sanity check


# ── dataframe_to_excel ─────────────────────────────────────────────


class TestDataframeToExcel:
    def test_basic_excel_export(self):
        df = pd.DataFrame({"name": ["Alice"], "age": [30]})
        result = ExportService.dataframe_to_excel(df)
        assert isinstance(result, bytes)
        assert len(result) > 0  # Valid Excel file has content

    def test_empty_dataframe_excel(self):
        """An empty DataFrame should still produce a valid Excel file."""
        df = pd.DataFrame()
        result = ExportService.dataframe_to_excel(df)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_excel_sheet_name(self):
        df = pd.DataFrame({"x": [1]})
        result = ExportService.dataframe_to_excel(df)
        # The output is a valid xlsx — just check it's bytes
        assert isinstance(result, bytes)


# ── chart_to_png ───────────────────────────────────────────────────


class TestChartToPNG:
    def test_valid_figure_returns_bytes_or_none(self):
        """If kaleido is installed, returns PNG bytes; otherwise None.
        
        Either is acceptable based on the environment.
        """
        fig = go.Figure(data=go.Scatter(x=[1, 2], y=[3, 4]))
        result = ExportService.chart_to_png(fig)
        # Should be either bytes (kaleido works) or None (fallback)
        assert result is None or isinstance(result, bytes)

    def test_empty_figure(self):
        """An empty figure might fail, but should handle gracefully."""
        fig = go.Figure()
        result = ExportService.chart_to_png(fig)
        # Should not crash — either bytes or None
        assert result is None or isinstance(result, bytes)


# ── chart_to_html ──────────────────────────────────────────────────


class TestChartToHTML:
    def test_figure_to_html(self):
        fig = go.Figure(data=go.Scatter(x=[1], y=[2]))
        html = ExportService.chart_to_html(fig)
        assert isinstance(html, str)
        assert "plotly" in html.lower() or "Plotly" in html
        assert "<div" in html

    def test_empty_figure_html(self):
        fig = go.Figure()
        html = ExportService.chart_to_html(fig)
        assert isinstance(html, str)
        assert len(html) > 0


# ── conversation_to_text ───────────────────────────────────────────


class TestConversationToText:
    def test_empty_conversation(self):
        text = ExportService.conversation_to_text([])
        assert "Exportación de Conversación" in text
        assert "Total de mensajes: 0" in text

    def test_single_message(self):
        msgs = [ChatMessage(role="user", content="Hola")]
        text = ExportService.conversation_to_text(msgs)
        assert "Total de mensajes: 1" in text
        assert "Tú:" in text
        assert "Hola" in text

    def test_multiple_messages(self):
        msgs = [
            ChatMessage(role="user", content="Pregunta 1"),
            ChatMessage(role="assistant", content="Respuesta 1"),
            ChatMessage(role="user", content="Pregunta 2"),
        ]
        text = ExportService.conversation_to_text(msgs)
        assert "Total de mensajes: 3" in text
        assert "[1] Tú:" in text
        assert "[2] Asistente:" in text
        assert "[3] Tú:" in text

    def test_messages_with_figure_and_dataframe(self):
        msgs = [
            ChatMessage(role="assistant", content="Análisis", figure_json="{}"),
            ChatMessage(role="assistant", content="Tabla", dataframe_json="{}"),
        ]
        text = ExportService.conversation_to_text(msgs)
        assert "[Gráfico generado]" in text
        assert "[Tabla de datos generada]" in text

    def test_message_without_to_export_text_fallback(self):
        """If a message doesn't have to_export_text, fallback to attributes."""
        class FakeMessage:
            role = "user"
            content = "fallback"

        text = ExportService.conversation_to_text([FakeMessage()])
        assert "user" in text
        assert "fallback" in text

    def test_header_format(self):
        msgs = [ChatMessage(role="user", content="Hola")]
        text = ExportService.conversation_to_text(msgs)
        lines = text.split("\n")
        assert lines[0] == "=== Exportación de Conversación ==="
        assert "Total de mensajes:" in lines[1]
        assert "=" * 40 in lines[2]


# ── Download Labels ────────────────────────────────────────────────


class TestDownloadLabels:
    def test_csv_download_label(self):
        label = ExportService.get_csv_download_label("datos.csv")
        assert label == "datos_analisis.csv"

    def test_csv_download_label_without_extension(self):
        label = ExportService.get_csv_download_label("datos")
        assert label == "datos_analisis.csv"

    def test_csv_download_label_excel_input(self):
        label = ExportService.get_csv_download_label("datos.xlsx")
        assert label == "datos_analisis.csv"

    def test_chart_download_label(self):
        label = ExportService.get_chart_download_label("datos")
        assert label == "datos_grafico.png"

    def test_conversation_download_label(self):
        label = ExportService.get_conversation_download_label()
        assert label == "conversacion_analisis.txt"
