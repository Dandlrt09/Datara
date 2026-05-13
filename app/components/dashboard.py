"""
Dashboard: displays accumulated charts and KPIs in a responsive grid layout.
Supports global filters that re-compute every item in real time.

Architecture (post-filter-refactor):
  - ``st.session_state.dashboard_items`` stores CONFIG only (not rendered figures)
  - At render time, the dashboard reads the raw data from FileService,
    applies global filters, and builds figures / computes metrics on the fly.
  - This means changing a filter updates ALL charts and KPIs simultaneously.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

from services.file_service import FileService
from app.components.chart_download import render_chart_with_download

# ─── Chart builders (same as chart_builder.py) ────────────────

CHART_BUILDERS = {
    "Barra": lambda df, kw: px.bar(df, **kw, barmode="group"),
    "Línea": lambda df, kw: px.line(df, **kw, markers=True),
    "Dispersión": lambda df, kw: px.scatter(df, **kw),
    "Torta": lambda df, kw: px.pie(df, **kw),
    "Histograma": lambda df, kw: px.histogram(df, **kw),
    "Box Plot": lambda df, kw: px.box(df, **kw),
}


# ─── Public entry point ──────────────────────────────────────


def render_dashboard(file_service: FileService) -> None:
    """Render the full dashboard: filters bar + all items (charts + KPIs)."""
    items = st.session_state.get("dashboard_items", [])
    if not items:
        return

    st.markdown("---")
    st.subheader("📊 Dashboard")
    st.caption(
        f"{len(items)} item(s) · "
        "Los filtros se aplican a todos los gráficos y KPIs automáticamente."
    )

    # ── Global filter bar ───────────────────────────────────
    _render_filter_bar(file_service, items)

    # ── Separate charts from KPIs ───────────────────────────
    chart_items = [it for it in items if it["config"].get("item_type", "chart") == "chart"]
    kpi_items = [it for it in items if it["config"].get("item_type") == "kpi"]

    # ── Render KPIs first (as metric cards) ────────────────
    if kpi_items:
        _render_kpi_row(kpi_items, file_service)

    # ── Render charts (2-column grid) ──────────────────────
    if chart_items:
        for i in range(0, len(chart_items), 2):
            row = chart_items[i : i + 2]
            cols = st.columns(len(row))
            for col, entry in zip(cols, row):
                with col:
                    _render_chart_card(entry, file_service)

    # ── Clear-all button ──────────────────────────────────
    n = len(items)
    if n > 1 and st.button("🗑️ Limpiar Dashboard", width="stretch", type="secondary"):
        st.session_state.dashboard_items = []
        st.session_state.dashboard_filters = {"columns": []}
        st.rerun()


# ─── Filters ─────────────────────────────────────────────────


def _render_filter_bar(file_service: FileService, items: list[dict]) -> None:
    """Render global filter controls.

    The user can add one or more column-based filters.
    Filters are stored in ``st.session_state.dashboard_filters``
    as ``{"columns": [{"col": "premium", "vals": ["yes"]}, ...]}``.
    """
    filters = st.session_state.setdefault("dashboard_filters", {"columns": []})

    # Gather all categorical columns from every referenced file
    all_cat_cols: list[str] = []
    seen: set[str] = set()
    for item in items:
        fname = item.get("file", "")
        fd = file_service.get_file(fname)
        if fd is not None:
            for col in fd.df.select_dtypes(exclude="number").columns:
                if col not in seen:
                    seen.add(col)
                    all_cat_cols.append(col)

    if not all_cat_cols:
        return

    st.markdown("##### 🔍 Filtros")

    # ── Existing filter rows ──────────────────────────────
    cols_to_remove: list[int] = []
    for idx, f in enumerate(filters["columns"]):
        c1, c2, c3 = st.columns([2, 3, 1])
        with c1:
            col_name = st.selectbox(
                "Columna",
                options=[""] + all_cat_cols,
                index=(all_cat_cols.index(f["col"]) + 1) if f.get("col") in all_cat_cols else 0,
                key=f"filter_col_{idx}",
            )
        with c2:
            if col_name:
                fd_for_vals = _first_file_with_col(file_service, items, col_name)
                unique_vals = sorted(fd_for_vals[col_name].dropna().unique()) if fd_for_vals is not None else []
                selected_vals = st.multiselect(
                    "Valores",
                    options=unique_vals,
                    default=f.get("vals", unique_vals) if f.get("vals") else unique_vals,
                    key=f"filter_vals_{idx}",
                )
                filters["columns"][idx] = {"col": col_name, "vals": list(selected_vals)}
            else:
                st.caption("(seleccioná una columna)")
                filters["columns"][idx] = {"col": "", "vals": []}
        with c3:
            st.caption("")
            if st.button("✕", key=f"filter_remove_{idx}"):
                cols_to_remove.append(idx)

    for idx in reversed(cols_to_remove):
        filters["columns"].pop(idx)

    # ── Add filter button ────────────────────────────────
    c1, c2 = st.columns([3, 1])
    with c1:
        if st.button("➕ Agregar filtro", width="stretch", type="secondary"):
            filters["columns"].append({"col": "", "vals": []})
            st.rerun()
    with c2:
        if filters["columns"] and st.button("✕ Limpiar filtros", width="stretch"):
            filters["columns"] = []
            st.rerun()

    st.markdown("---")


def _first_file_with_col(
    file_service: FileService, items: list[dict], col: str,
) -> Optional[pd.DataFrame]:
    """Return the first DataFrame that contains *col* among all referenced files."""
    for item in items:
        fname = item.get("file", "")
        fd = file_service.get_file(fname)
        if fd is not None and col in fd.df.columns:
            return fd.df
    return None


# ─── KPI rendering ───────────────────────────────────────────


def _render_kpi_row(kpi_items: list[dict], file_service: FileService) -> None:
    """Render KPIs as metric cards in a single row."""
    kpis = []
    for entry in kpi_items:
        val = _compute_kpi(entry, file_service)
        kpis.append((entry, val))

    cols = st.columns(len(kpis))
    for col, (entry, val) in zip(cols, kpis):
        with col:
            title = entry.get("title", "KPI")
            cfg = entry["config"]
            agg_label = cfg.get("aggregation", "mean")
            col_name = cfg.get("column", "")
            group_by = cfg.get("group_by")

            if isinstance(val, dict):
                # Grouped KPIs → one metric per group
                for group_label, group_val in val.items():
                    st.metric(
                        label=f"{title} — {group_label}",
                        value=_format_metric(group_val, col_name),
                    )
            else:
                st.metric(label=title, value=_format_metric(val, col_name))

    # Remove button for each KPI
    for entry in kpi_items:
        if st.button("🗑️ Eliminar", key=f"del_kpi_{entry['id']}", width="stretch"):
            _remove_item(entry["id"])
            st.rerun()


def _compute_kpi(entry: dict, file_service: FileService) -> float | dict:
    """Compute a KPI value from config + filtered data."""
    df = _get_filtered_df(entry.get("file", ""), file_service)
    if df is None or df.empty:
        return 0
    return _compute_kpi_value(df, entry.get("config", {}))


def _compute_kpi_value(df: pd.DataFrame, config: dict) -> float | dict:
    """Pure: compute a KPI value from a DataFrame + config (no mocks needed).

    Returns:
        float for ungrouped KPIs, or ``{group_label: value}`` for grouped KPIs.
    """
    col = config.get("column", "")
    agg = config.get("aggregation", "mean")
    group_by = config.get("group_by")

    if col not in df.columns:
        return 0

    if group_by and group_by in df.columns:
        result = df.groupby(group_by)[col].agg(agg)
        return result.to_dict()
    else:
        return float(df[col].agg(agg))


def _format_metric(val: float, col_name: str = "") -> str:
    """Format a metric value nicely."""
    if val is None:
        return "—"
    if isinstance(val, float):
        if abs(val) >= 1_000_000:
            return f"${val:,.0f}" if "price" in col_name.lower() else f"{val:,.0f}"
        elif abs(val) >= 1_000:
            return f"${val:,.0f}" if "price" in col_name.lower() else f"{val:,.1f}"
        elif val == int(val):
            return f"{int(val)}"
        else:
            return f"{val:.2f}"
    return str(val)


# ─── Chart rendering ─────────────────────────────────────────


def _render_chart_card(entry: dict, file_service: FileService) -> None:
    """Render a single chart card with title, plot, and remove button."""
    title = entry.get("title", "Gráfico")
    chart_id = entry.get("id", "")

    st.caption(f"**{title}**")

    fig = _build_chart_from_config(entry, file_service)

    if fig is not None:
        render_chart_with_download(fig, entry.get("timestamp", ""))
    else:
        st.info("⚠️ No se pudo generar el gráfico (verificá que los datos sigan disponibles).")

    if st.button("🗑️ Eliminar", key=f"del_chart_{chart_id}", width="stretch"):
        _remove_item(chart_id)
        st.rerun()


def _build_chart_from_config(entry: dict, file_service: FileService) -> Optional[go.Figure]:
    """Build a Plotly figure from a dashboard item's config + filtered data."""
    df = _get_filtered_df(entry.get("file", ""), file_service)
    return _build_chart_figure(df, entry.get("config", {}), entry.get("title"))


def _build_chart_figure(
    df: Optional[pd.DataFrame],
    config: dict,
    title: Optional[str] = None,
) -> Optional[go.Figure]:
    """Pure: build a Plotly figure from a DataFrame + config (no mocks needed).

    Returns ``None`` if the config is invalid or the DataFrame is empty.
    """
    if df is None or df.empty:
        return None

    chart_type = config.get("chart_type", "")
    mappings = config.get("mappings", {})
    plotly_kw: dict[str, str] = {k: v for k, v in mappings.items() if v}

    builder = CHART_BUILDERS.get(chart_type)
    if builder is None:
        return None

    try:
        fig = builder(df, plotly_kw)
        fig.update_layout(
            template="plotly_white",
            margin=dict(l=40, r=40, t=40, b=40),
            title=title or None,
        )
        return fig
    except Exception:
        return None


# ─── Data helpers ────────────────────────────────────────────


def _get_filtered_df(filename: str, file_service: FileService) -> Optional[pd.DataFrame]:
    """Get the DataFrame for *filename* with all global filters applied."""
    fd = file_service.get_file(filename)
    if fd is None:
        return None
    df = fd.df.copy()
    filters = st.session_state.get("dashboard_filters", {"columns": []})
    return _apply_filters(df, filters)


def _apply_filters(df: pd.DataFrame, filters: Optional[dict]) -> pd.DataFrame:
    """Pure: apply filter config to a DataFrame (no mocks needed)."""
    if not filters:
        return df.copy()
    result = df.copy()
    for f in filters.get("columns", []):
        col = f.get("col", "")
        vals = f.get("vals", [])
        if col and vals and col in result.columns:
            result = result[result[col].isin(vals)]
    return result


def _remove_item(item_id: str) -> None:
    """Remove a dashboard item by ID."""
    items = st.session_state.get("dashboard_items", [])
    items[:] = [it for it in items if it.get("id") != item_id]
