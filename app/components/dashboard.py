"""
Dashboard: displays accumulated charts in a responsive grid layout.

Charts are stored in ``st.session_state.dashboard_charts`` as a list of dicts
with keys: id, title, chart_type, figure_json, timestamp.

Each chart can be individually removed, or the entire dashboard cleared.
"""

from __future__ import annotations

import plotly.io as pio
import streamlit as st

from app.components.chart_download import render_chart_with_download


def render_dashboard() -> None:
    """Render all dashboard charts in a 2-column grid.

    If there are no charts, this function does nothing.
    """
    charts = st.session_state.get("dashboard_charts", [])
    if not charts:
        return

    st.markdown("---")
    st.subheader("📊 Dashboard")
    st.caption(
        f"{len(charts)} gráfico(s) · "
        "Los datos se pierden al cerrar la sesión."
    )

    # Render charts in a 2-column grid
    for i in range(0, len(charts), 2):
        row = charts[i : i + 2]
        cols = st.columns(len(row))

        for col, entry in zip(cols, row):
            with col:
                _render_chart_card(entry)

    # Clear-all button
    n = len(charts)
    if n > 1 and st.button(
        "🗑️ Limpiar Dashboard",
        width="stretch",
        type="secondary",
    ):
        st.session_state.dashboard_charts = []
        st.rerun()


def _render_chart_card(entry: dict) -> None:
    """Render a single chart card with title, plot, and remove button."""
    title = entry.get("title", "Gráfico")
    timestamp = entry.get("timestamp", "")
    chart_id = entry.get("id", "")

    st.caption(f"**{title}**")

    try:
        fig = pio.from_json(entry["figure_json"])
        render_chart_with_download(fig, timestamp)
    except Exception:
        st.error("No se pudo renderizar el gráfico guardado.")

    # Remove button
    if st.button(
        "🗑️ Eliminar",
        key=f"del_chart_{chart_id}",
        width="stretch",
    ):
        charts = st.session_state.dashboard_charts
        charts[:] = [c for c in charts if c.get("id") != chart_id]
        st.rerun()
