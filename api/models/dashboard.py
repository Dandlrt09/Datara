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
