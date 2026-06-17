from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class DashboardItem(BaseModel):
    """A single dashboard tile (chart or KPI)."""

    id: str
    title: str
    chart_type: str  # e.g. "bar", "line", "kpi"
    figure_html: Optional[str] = None
    kpi_value: Optional[str] = None


class DashboardResponse(BaseModel):
    """Response returned for ``GET /api/dashboard``."""

    items: list[DashboardItem]


class BuildChartRequest(BaseModel):
    """Request to build a chart/KPI from file data + config (no LLM)."""

    file: str
    chart_type: str  # "Barra", "Línea", "Torta", etc., or "kpi"
    title: str = ""
    mappings: dict[str, str] = {}  # e.g. {"x": "col_a", "y": "col_b", "color": "col_c"}
    aggregation: str = ""  # for KPIs: "mean", "sum", "count", "min", "max"
    group_by: str = ""


class BuildChartResponse(BaseModel):
    """Response from building a chart/KPI server-side."""

    figure_html: Optional[str] = None
    kpi_value: Optional[str] = None
    error: Optional[str] = None
