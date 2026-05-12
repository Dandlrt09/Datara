from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ChatMessage:
    """A single entry in the chat conversation."""

    role: str  # "user" or "assistant"
    content: str
    figure_json: Optional[str] = None  # Plotly figure as JSON
    dataframe_json: Optional[str] = None  # DataFrame as JSON (split orient)
    timestamp: datetime = field(default_factory=datetime.now)
    error: bool = False

    def to_export_text(self, index: int) -> str:
        """Format message for text export."""
        role_label = "Tú" if self.role == "user" else "Asistente"
        text = f"[{index}] {role_label}:\n{self.content}\n"
        if self.figure_json:
            text += "[Gráfico generado]\n"
        if self.dataframe_json:
            text += "[Tabla de datos generada]\n"
        return text + "\n"
