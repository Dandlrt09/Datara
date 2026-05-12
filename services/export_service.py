"""
Export Service: handles downloading results as CSV, PNG, and TXT.
"""

from __future__ import annotations

import io
import csv
from typing import Optional

import pandas as pd
import plotly.graph_objects as go


class ExportService:
    """Provides export functionality for charts, dataframes, and conversations."""

    @staticmethod
    def chart_to_png(figure: go.Figure) -> Optional[bytes]:
        """
        Convert a Plotly figure to PNG bytes.

        Requires kaleido or orca to be installed.
        Returns None if conversion fails.
        """
        try:
            img_bytes = figure.to_image(format="png", width=1200, height=800, scale=2)
            return img_bytes
        except Exception:
            # Fallback: return HTML
            return None

    @staticmethod
    def chart_to_html(figure: go.Figure) -> str:
        """Convert a Plotly figure to an HTML div string."""
        return figure.to_html(include_plotlyjs="cdn", full_html=False)

    @staticmethod
    def dataframe_to_csv(df: pd.DataFrame) -> bytes:
        """Convert a DataFrame to CSV bytes."""
        output = io.BytesIO()
        df.to_csv(output, index=False, encoding="utf-8-sig")
        output.seek(0)
        return output.getvalue()

    @staticmethod
    def dataframe_to_excel(df: pd.DataFrame) -> bytes:
        """Convert a DataFrame to Excel bytes."""
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Datos")
        output.seek(0)
        return output.getvalue()

    @staticmethod
    def conversation_to_text(messages: list) -> str:
        """
        Convert a list of ChatMessage objects to a text string.

        Args:
            messages: List of ChatMessage-like objects with role, content,
                     to_export_text() methods

        Returns:
            Formatted conversation text
        """
        lines = [
            "=== Exportación de Conversación ===",
            f"Total de mensajes: {len(messages)}",
            "=" * 40,
            "",
        ]

        for i, msg in enumerate(messages, 1):
            if hasattr(msg, "to_export_text"):
                lines.append(msg.to_export_text(i))
            else:
                role = getattr(msg, "role", "unknown")
                content = getattr(msg, "content", "")
                lines.append(f"[{i}] {role}: {content}\n")

        return "\n".join(lines)

    @staticmethod
    def get_csv_download_label(filename: str) -> str:
        """Generate a user-friendly download filename for a CSV."""
        base = filename.rsplit(".", 1)[0] if "." in filename else filename
        return f"{base}_analisis.csv"

    @staticmethod
    def get_chart_download_label(filename: str) -> str:
        """Generate a user-friendly download filename for a chart."""
        return f"{filename}_grafico.png"

    @staticmethod
    def get_conversation_download_label() -> str:
        """Generate a download filename for a conversation export."""
        return "conversacion_analisis.txt"
