from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd
import plotly.graph_objects as go


@dataclass
class AnalysisResult:
    """Result from executing LLM-generated analysis code."""

    text: str = ""
    figure: Optional[go.Figure] = None
    dataframe: Optional[pd.DataFrame] = None
    error: Optional[str] = None
    code_executed: str = ""

    @property
    def success(self) -> bool:
        return self.error is None

    @property
    def has_figure(self) -> bool:
        return self.figure is not None

    @property
    def has_dataframe(self) -> bool:
        return self.dataframe is not None
