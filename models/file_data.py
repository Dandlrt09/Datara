from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd


@dataclass
class FileData:
    """Represents an uploaded file with its parsed data."""

    filename: str
    df: pd.DataFrame
    sheet_name: str = ""
    size_bytes: int = 0
    rows: int = 0
    columns: int = 0
    dtypes: dict[str, str] = field(default_factory=dict)
    loaded_at: datetime = field(default_factory=datetime.now)
    display_name: str = ""

    def __post_init__(self):
        if not self.display_name:
            self.display_name = self.filename
        self.rows = len(self.df)
        self.columns = len(self.df.columns)
        self.dtypes = {col: str(dtype) for col, dtype in self.df.dtypes.items()}

    def summary(self) -> str:
        """Return a text summary for LLM context."""
        cols_info = "\n".join(
            f"  - {col}: {dtype}" for col, dtype in self.dtypes.items()
        )
        return (
            f"Archivo: {self.display_name}\n"
            f"Filas: {self.rows} | Columnas: {self.columns}\n"
            f"Columnas:\n{cols_info}\n"
            f"Primeras 5 filas:\n{self.df.head(5).to_string()}\n"
        )

    @property
    def is_empty(self) -> bool:
        return self.df.empty
