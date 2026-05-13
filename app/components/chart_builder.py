"""
Chart Builder: UI for users to configure and create Plotly charts interactively.
No LLM involved — deterministic chart generation via Plotly Express.

The user picks a file, chart type, and column mappings from a form,
and the chart is added directly to the session dashboard.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

from services.file_service import FileService

# ─── Chart type definitions ──────────────────────────────────

CHART_TYPES: dict[str, dict] = {
    "Barra": {
        "icon": "📊",
        "params": ["x", "y", "color"],
    },
    "Línea": {
        "icon": "📈",
        "params": ["x", "y", "color"],
    },
    "Dispersión": {
        "icon": "🔵",
        "params": ["x", "y", "color", "size"],
    },
    "Torta": {
        "icon": "🥧",
        "params": ["names", "values"],
    },
    "Histograma": {
        "icon": "📋",
        "params": ["x", "color"],
    },
    "Box Plot": {
        "icon": "📦",
        "params": ["x", "y", "color"],
    },
}

PARAM_LABELS: dict[str, str] = {
    "x": "Eje X",
    "y": "Eje Y",
    "color": "Color / Agrupar",
    "size": "Tamaño (opcional)",
    "names": "Categorías",
    "values": "Valores",
}

# Required params per chart type (the rest are optional)
REQUIRED_PARAMS: dict[str, list[str]] = {
    "Barra": ["x", "y"],
    "Línea": ["x", "y"],
    "Dispersión": ["x", "y"],
    "Torta": ["names", "values"],
    "Histograma": ["x"],
    "Box Plot": ["y"],
}

# Builders map: chart_type → callable(df, kwargs) → Figure
CHART_BUILDERS: dict[str, Callable] = {
    "Barra": lambda df, kw: px.bar(df, **kw, barmode="group"),
    "Línea": lambda df, kw: px.line(df, **kw, markers=True),
    "Dispersión": lambda df, kw: px.scatter(df, **kw),
    "Torta": lambda df, kw: px.pie(df, **kw),
    "Histograma": lambda df, kw: px.histogram(df, **kw),
    "Box Plot": lambda df, kw: px.box(df, **kw),
}


def render_chart_builder(file_service: FileService) -> None:
    """Render the chart builder UI inside the chat view.

    The user selects file, chart type, and column mappings via a form.
    On submit, the Plotly figure is built and appended to
    ``st.session_state.dashboard_charts``.

    NOTE: The file and chart-type selectors are deliberately OUTSIDE the form
    so that changing them triggers an immediate rerun, which updates the
    dynamic parameter fields (axis mappings) to match the selected chart type.
    """
    filenames = file_service.get_filenames()
    if not filenames:
        st.info("📂 Primero cargá un archivo de datos para crear gráficos.")
        return

    # Build df_map once
    df_map: dict[str, pd.DataFrame] = {}
    for fname in filenames:
        fd = file_service.get_file(fname)
        if fd is not None:
            df_map[fname] = fd.df

    if not df_map:
        st.info("📂 No hay datos disponibles en los archivos cargados.")
        return

    st.markdown("---")
    st.subheader("📊 Constructor de Gráficos")

    # ── File selector (OUTSIDE form — triggers rerun) ──────────
    selected_file = st.selectbox(
        "📄 Archivo",
        options=list(df_map.keys()),
        key="cb_file",
    )
    df = df_map[selected_file]
    all_cols: list[str] = df.columns.tolist()
    num_cols: list[str] = df.select_dtypes(include="number").columns.tolist()

    # ── Chart type (OUTSIDE form — triggers rerun) ────────────
    chart_type = st.selectbox(
        "📐 Tipo de gráfico",
        options=list(CHART_TYPES.keys()),
        format_func=lambda t: f"{CHART_TYPES[t]['icon']} {t}",
        key="cb_type",
    )

    # Know which params we need BEFORE entering the form
    params: list[str] = CHART_TYPES[chart_type]["params"]
    required = set(REQUIRED_PARAMS.get(chart_type, []))

    # ── Column mappings (INSIDE form — batch submit) ──────────
    with st.form("chart_builder_form", clear_on_submit=False):
        mappings: dict[str, Optional[str]] = {}

        for idx in range(0, len(params), 2):
            cols = st.columns(2)
            p1 = params[idx]
            with cols[0]:
                mappings[p1] = _param_selector(
                    p1, all_cols, num_cols, is_required=(p1 in required),
                )
            if idx + 1 < len(params):
                p2 = params[idx + 1]
                with cols[1]:
                    mappings[p2] = _param_selector(
                        p2, all_cols, num_cols, is_required=(p2 in required),
                    )

        # ── Title ────────────────────────────────────────────
        title = st.text_input("🏷️ Título del gráfico (opcional)", key="cb_title")

        st.caption(
            "💡 Los gráficos se agregan al Dashboard y se pierden al cerrar la sesión."
        )

        submitted = st.form_submit_button(
            "➕ Agregar al Dashboard",
            type="primary",
            width="stretch",
        )

    # ── Handle submission (outside the form context) ────────
    if submitted:
        _add_chart_to_dashboard(df, chart_type, mappings, title)


# ─── Internal helpers ────────────────────────────────────────


def _param_selector(
    param: str,
    all_cols: list[str],
    num_cols: list[str],
    is_required: bool = False,
) -> Optional[str]:
    """Render a single parameter selector (selectbox).

    Args:
        param: Parameter key (x, y, color, size, names, values).
        all_cols: All column names from the DataFrame.
        num_cols: Only numeric-column names.
        is_required: Whether the user MUST pick a column.

    Returns:
        Selected column name, or ``None`` if left empty.
    """
    label = PARAM_LABELS.get(param, param)

    # Determine which columns to show
    if param in ("y", "values", "size"):
        options = list(num_cols)
    else:
        options = list(all_cols)

    # Add empty option for non-required params
    if not is_required:
        options.insert(0, "")

    if not options or (len(options) == 1 and options[0] == ""):
        st.caption(f"❌ No hay columnas {'numéricas' if param in ('y', 'values', 'size') else 'disponibles'} para {label.lower()}")
        return None

    selected = st.selectbox(label, options=options, key=f"cb_{param}")

    # If empty string was chosen, treat as None
    if not is_required and not selected:
        return None

    return selected if selected else None


def _add_chart_to_dashboard(
    df: pd.DataFrame,
    chart_type: str,
    mappings: dict[str, Optional[str]],
    title: str,
) -> None:
    """Build the Plotly figure and append it to the dashboard state.

    Displays an ``st.error`` message on failure instead of crashing.
    """
    # Filter: keep only non-None, non-empty values
    plotly_kw: dict[str, str] = {
        k: v for k, v in mappings.items() if v
    }

    # Validate required params
    required = set(REQUIRED_PARAMS.get(chart_type, []))
    missing = required - set(plotly_kw.keys())
    if missing:
        labels = [PARAM_LABELS.get(p, p) for p in missing]
        st.error(f"Faltan parámetros requeridos: {', '.join(labels)}")
        return

    try:
        builder = CHART_BUILDERS.get(chart_type)
        if builder is None:
            st.error(f"Tipo de gráfico no soportado: {chart_type}")
            return

        fig = builder(df, plotly_kw)

        # Improve layout defaults
        fig.update_layout(
            template="plotly_white",
            margin=dict(l=40, r=40, t=40, b=40),
            title=title if title else None,
        )

        chart_entry = {
            "id": f"chart_{datetime.now().strftime('%H%M%S_%f')}",
            "title": title or f"{chart_type} — {datetime.now().strftime('%H:%M')}",
            "chart_type": chart_type,
            "figure_json": pio.to_json(fig),
            "timestamp": datetime.now().isoformat(),
        }

        st.session_state.setdefault("dashboard_charts", []).append(chart_entry)
        st.rerun()

    except Exception as e:
        st.error(f"Error al crear el gráfico: {e}")
