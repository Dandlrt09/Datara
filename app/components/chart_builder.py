"""
Chart Builder: UI for users to configure and create charts, KPIs, and dashboard items.
No LLM involved — deterministic chart generation via Plotly Express.

Architecture (post-filter-refactor):
  - The builder stores CONFIG, not rendered figures
  - At render time the dashboard reconstructs charts/KPIs from config + current data
  - This allows global filters to affect ALL items on the dashboard
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

import pandas as pd
import plotly.express as px
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
    "Indicadores (KPIs)": {
        "icon": "🏷️",
        "params": [],  # KPIs use a separate UI section
    },
}

PARAM_LABELS: dict[str, str] = {
    "x": "Eje X",
    "y": "Eje Y",
    "color": "Agrupar por",
    "size": "Tamaño (opcional)",
    "names": "Categorías",
    "values": "Valores",
}

REQUIRED_PARAMS: dict[str, list[str]] = {
    "Barra": ["x", "y"],
    "Línea": ["x", "y"],
    "Dispersión": ["x", "y"],
    "Torta": ["names", "values"],
    "Histograma": ["x"],
    "Box Plot": ["y"],
}

CHART_BUILDERS: dict[str, Callable] = {
    "Barra": lambda df, kw: px.bar(df, **kw, barmode="group"),
    "Línea": lambda df, kw: px.line(df, **kw, markers=True),
    "Dispersión": lambda df, kw: px.scatter(df, **kw),
    "Torta": lambda df, kw: px.pie(df, **kw),
    "Histograma": lambda df, kw: px.histogram(df, **kw),
    "Box Plot": lambda df, kw: px.box(df, **kw),
}

# ─── KPI definitions ─────────────────────────────────────────

AGGREGATIONS: dict[str, str] = {
    "Promedio": "mean",
    "Suma": "sum",
    "Conteo": "count",
    "Mínimo": "min",
    "Máximo": "max",
}

AGGREGATION_LABELS: dict[str, str] = {v: k for k, v in AGGREGATIONS.items()}


# ─── Main entry point ────────────────────────────────────────


def render_chart_builder(file_service: FileService) -> None:
    """Render the chart builder UI inside the chat view.

    The user selects file, chart type, and column mappings via a form.
    On submit, the item CONFIG is appended to
    ``st.session_state.dashboard_items`` (the figure is NOT built here;
    it is reconstructed at render time so global filters can apply).
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

    # ── File selector (OUTSIDE form) ──────────────────────────
    selected_file = st.selectbox(
        "📄 Archivo",
        options=list(df_map.keys()),
        key="cb_file",
    )
    df = df_map[selected_file]
    all_cols: list[str] = df.columns.tolist()
    num_cols: list[str] = df.select_dtypes(include="number").columns.tolist()
    cat_cols: list[str] = df.select_dtypes(exclude="number").columns.tolist()

    # ── Chart type (OUTSIDE form — pills instead of selectbox
    #    to avoid the scroll-issue on long pages) ──────────────
    chart_type = st.pills(
        "📐 Tipo",
        options=list(CHART_TYPES.keys()),
        format_func=lambda t: f"{CHART_TYPES[t]['icon']} {t}",
        selection_mode="single",
        default="Barra",
        key="cb_type",
    )

    is_kpi = chart_type == "Indicadores (KPIs)"

    if not is_kpi:
        params: list[str] = CHART_TYPES[chart_type]["params"]
        required = set(REQUIRED_PARAMS.get(chart_type, []))
    else:
        params = []
        required = set()

    # ── Form: column mappings / KPI config ───────────────────
    with st.form("chart_builder_form", clear_on_submit=False):
        config: dict = {}

        if is_kpi:
            # ── KPI fields ──────────────────────────────────
            config["item_type"] = "kpi"
            config["column"] = st.selectbox(
                "📏 Columna numérica", options=num_cols, key="cb_kpi_col",
            )
            agg_label = st.selectbox(
                "📐 Agregación",
                options=list(AGGREGATIONS.keys()),
                key="cb_kpi_agg",
            )
            config["aggregation"] = AGGREGATIONS[agg_label]
            config["group_by"] = st.selectbox(
                "🔀 Agrupar por (opcional)",
                options=[""] + cat_cols,
                key="cb_kpi_group",
            )
            if not config["group_by"]:
                config["group_by"] = None

        else:
            # ── Chart param selectors ───────────────────────
            config["item_type"] = "chart"
            config["chart_type"] = chart_type
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

            config["mappings"] = mappings

        # ── Title ────────────────────────────────────────────
        title = st.text_input("🏷️ Título (opcional)", key="cb_title")

        st.caption("💡 Los items se agregan al Dashboard y reaccionan a los filtros globales.")

        submitted = st.form_submit_button(
            "➕ Agregar al Dashboard",
            type="primary",
            width="stretch",
        )

    if submitted:
        _add_item_to_dashboard(selected_file, title, config)


# ─── Internal helpers ────────────────────────────────────────


def _param_selector(
    param: str,
    all_cols: list[str],
    num_cols: list[str],
    is_required: bool = False,
) -> Optional[str]:
    """Render a single parameter selector (selectbox)."""
    label = PARAM_LABELS.get(param, param)

    if param in ("y", "values", "size"):
        options = list(num_cols)
    else:
        options = list(all_cols)

    if not is_required:
        options.insert(0, "")

    if not options or (len(options) == 1 and options[0] == ""):
        st.caption(
            f"❌ No hay columnas "
            f"{'numéricas' if param in ('y', 'values', 'size') else 'disponibles'}"
            f" para {label.lower()}"
        )
        return None

    selected = st.selectbox(label, options=options, key=f"cb_{param}")

    if not is_required and not selected:
        return None

    return selected if selected else None


def _add_item_to_dashboard(
    filename: str,
    title: str,
    config: dict,
) -> None:
    """Validate and append a dashboard item (chart config or KPI config).

    Stores CONFIG only — the actual figure/metric is built at render time
    so that global filters can affect every item.
    """
    item_type = config.get("item_type", "chart")

    # ── Validate KPI ──────────────────────────────────────
    if item_type == "kpi":
        if not config.get("column"):
            st.error("Seleccioná una columna numérica para el KPI.")
            return

    # ── Validate chart ────────────────────────────────────
    else:
        chart_type = config.get("chart_type", "")
        mappings = config.get("mappings", {})
        required = set(REQUIRED_PARAMS.get(chart_type, []))
        plotly_kw = {k: v for k, v in mappings.items() if v}
        missing = required - set(plotly_kw.keys())
        if missing:
            labels = [PARAM_LABELS.get(p, p) for p in missing]
            st.error(f"Faltan parámetros requeridos: {', '.join(labels)}")
            return

    now = datetime.now()

    entry: dict = {
        "id": f"item_{now.strftime('%H%M%S_%f')}",
        "title": title or f"{config.get('chart_type', 'KPI')} — {now.strftime('%H:%M')}",
        "file": filename,
        "config": config,
        "timestamp": now.isoformat(),
    }

    st.session_state.setdefault("dashboard_items", []).append(entry)
    st.rerun()
