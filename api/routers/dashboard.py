"""Dashboard router — KPI + chart items management.

Endpoints
---------
- ``GET    /api/dashboard``              → all items (with optional filter)
- ``POST   /api/dashboard``              → add an item (chart or KPI)
- ``POST   /api/dashboard/build``        → build chart/KPI from file data + config
- ``DELETE /api/dashboard/{item_id}``    → remove an item
"""

from __future__ import annotations

from time import time
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_session
from api.models import (
    BuildChartRequest,
    BuildChartResponse,
    DashboardItem,
    DashboardResponse,
)
from api.session_data import SessionData
from services.plotly_theme import apply_datara_theme

router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(get_session)],
)


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    session: SessionData = Depends(get_session),
    filter_col: Optional[str] = Query(None, description="Column to filter on"),
    filter_vals: Optional[str] = Query(None, description="Comma-separated filter values"),
) -> DashboardResponse:
    """Return all dashboard items.

    Optional query parameters ``filter_col`` and ``filter_vals`` are
    stored in ``dashboard_filters`` for the session so the frontend
    can re-apply them when rebuilding figures.
    """
    # Persist filter (frontend will re-render with filter applied)
    if filter_col and filter_vals:
        session.dashboard_filters[filter_col] = [v.strip() for v in filter_vals.split(",")]

    items = [
        DashboardItem(
            id=item.get("id", ""),
            title=item.get("title", "Untitled"),
            chart_type=item.get("chart_type", ""),
            figure_html=item.get("figure_html"),
            kpi_value=item.get("kpi_value"),
        )
        for item in session.dashboard_items
    ]

    return DashboardResponse(items=items)


@router.post("", status_code=201, response_model=DashboardItem)
async def add_dashboard_item(
    body: dict,
    session: SessionData = Depends(get_session),
) -> DashboardItem:
    """Add a new dashboard item.

    Expected body::

        {"title": "...", "chart_type": "bar", "figure_html": "...", "config": {...}}

    The ``config`` dict is stored as-is and can contain chart type,
    column mappings, aggregation, etc.
    If ``figure_html`` or ``kpi_value`` are provided they are stored
    and returned immediately — no rebuild needed.
    """
    item_id = f"item_{int(time() * 1000)}"

    entry: dict = {
        "id": item_id,
        "title": body.get("title", "Untitled"),
        "chart_type": body.get("chart_type", ""),
        "figure_html": body.get("figure_html"),
        "kpi_value": body.get("kpi_value"),
        "file": body.get("file", ""),
        "config": body.get("config", {}),
    }
    session.dashboard_items.append(entry)

    return DashboardItem(
        id=item_id,
        title=entry["title"],
        chart_type=entry["chart_type"],
        figure_html=entry["figure_html"],
        kpi_value=entry["kpi_value"],
    )


# ─── Chart builders (deterministic, no LLM) ─────────────────────

CHART_BUILDERS: dict[str, callable] = {
    "Barra": lambda df, kw: px.bar(df, **kw, barmode="group"),
    "Linea": lambda df, kw: px.line(df, **kw, markers=True),
    "Dispersion": lambda df, kw: px.scatter(df, **kw),
    "Torta": lambda df, kw: px.pie(df, **kw),
    "Histograma": lambda df, kw: px.histogram(df, **kw),
    "Box Plot": lambda df, kw: px.box(df, **kw),
}

AGGREGATIONS: dict[str, str] = {
    "Promedio": "mean",
    "Suma": "sum",
    "Conteo": "count",
    "Minimo": "min",
    "Maximo": "max",
}

REQUIRED_PARAMS: dict[str, list[str]] = {
    "Barra": ["x", "y"],
    "Linea": ["x", "y"],
    "Dispersion": ["x", "y"],
    "Torta": ["names", "values"],
    "Histograma": ["x"],
    "Box Plot": ["y"],
}


@router.post("/build", response_model=BuildChartResponse)
async def build_chart(
    body: BuildChartRequest,
    session: SessionData = Depends(get_session),
) -> BuildChartResponse:
    """Build a chart or KPI from file data + config (no LLM involved).

    Request body::

        {
            "file": "ventas.csv",
            "chart_type": "Barra",        # or "kpi"
            "title": "Ventas por region",
            "mappings": {"x": "region", "y": "total", "color": "anio"},
            "aggregation": "sum",         # for KPIs
            "group_by": "region"          # for KPIs (optional)
        }

    Returns ``figure_html`` (for charts) or ``kpi_value`` (for KPIs).
    """
    fd = session.file_service.get_file(body.file)
    if fd is None:
        return BuildChartResponse(error=f"Archivo no encontrado: {body.file}")
    df = fd.df

    # ── KPI path ─────────────────────────────────────────────
    if body.chart_type.lower() == "kpi":
        col = body.mappings.get("value", "")
        if not col and body.mappings.get("y"):
            col = body.mappings["y"]
        if not col:
            return BuildChartResponse(error="Seleccioná una columna numérica para el KPI.")
        if col not in df.columns:
            return BuildChartResponse(error=f"Columna '{col}' no encontrada en los datos.")

        agg_func = body.aggregation or "mean"
        try:
            if body.group_by and body.group_by in df.columns:
                result = df.groupby(body.group_by)[col].agg(agg_func)
                kpi_value = ", ".join(f"{k}: {v:.2f}" for k, v in result.items())
            else:
                val = float(df[col].agg(agg_func))
                if val == int(val) if not pd.isna(val) else False:
                    kpi_value = f"{int(val)}"
                else:
                    kpi_value = f"{val:.2f}"
        except Exception as e:
            return BuildChartResponse(error=f"Error al calcular KPI: {e}")

        return BuildChartResponse(kpi_value=kpi_value)

    # ── Chart path ───────────────────────────────────────────
    builder = CHART_BUILDERS.get(body.chart_type)
    if builder is None:
        return BuildChartResponse(
            error=f"Tipo de gráfico no soportado: {body.chart_type}. "
                  f"Usá: {', '.join(CHART_BUILDERS.keys())} o 'kpi'."
        )

    # Validate required params
    required = REQUIRED_PARAMS.get(body.chart_type, [])
    plotly_kw: dict[str, str] = {k: v for k, v in body.mappings.items() if v}
    missing = [p for p in required if p not in plotly_kw]
    if missing:
        return BuildChartResponse(
            error=f"Parámetros requeridos faltantes: {', '.join(missing)}"
        )

    try:
        fig = builder(df, plotly_kw)
        fig = apply_datara_theme(fig)
        if body.title:
            fig.update_layout(title=body.title)
        figure_html = fig.to_html(
            include_plotlyjs=False,
            full_html=False,
            div_id=f"chart-build-{int(time() * 1000)}",
        )
        return BuildChartResponse(figure_html=figure_html)
    except Exception as e:
        return BuildChartResponse(error=f"Error al generar gráfico: {e}")


@router.delete("/{item_id}", status_code=204)
async def delete_dashboard_item(
    item_id: str,
    session: SessionData = Depends(get_session),
) -> None:
    """Remove a dashboard item by ID.  Returns ``404`` if not found."""
    for idx, existing in enumerate(session.dashboard_items):
        if existing.get("id") == item_id:
            session.dashboard_items.pop(idx)
            return

    raise HTTPException(
        status_code=404,
        detail=f"Dashboard item '{item_id}' not found",
    )
