"""
Datara custom Plotly theme — color palette and layout defaults.

Apply to any figure before export to ensure consistent brand-aligned
visuals across all charts (chat, dashboard, reports).
"""

from __future__ import annotations

import plotly.graph_objects as go

# ── Datara color palette (dark-theme optimized) ─────────────────
# These colors are vibrant, distinguishable, and read well on
# dark backgrounds (#0D1117 / #151a21).
DATARA_COLORS: list[str] = [
    "#99a8ff",  # primary blue
    "#22d3ee",  # cyan
    "#34d399",  # green
    "#fbbf24",  # amber
    "#fb7185",  # coral
    "#a78bfa",  # purple
    "#f472b6",  # pink
    "#818cf8",  # indigo
    "#2dd4bf",  # teal
    "#fdba74",  # orange
]

# Colors for categorical sequences (e.g. stacked bars, groups)
DATARA_DIVERGING: list[str] = [
    "#99a8ff",
    "#fb7185",
    "#34d399",
    "#fbbf24",
    "#a78bfa",
]

# Sequential color scale (single-hue, for heatmaps etc.)
DATARA_SEQUENTIAL: list[str] = [
    "#2a2f35",
    "#4866f7",
    "#748aff",
    "#99a8ff",
    "#bac3ff",
]


def apply_datara_theme(fig: go.Figure) -> go.Figure:
    """Apply the Datara visual theme to a Plotly figure in-place.

    Sets dark-mode-friendly defaults for fonts, gridlines, background,
    and the color sequence.  Chart-specific settings (axis titles,
    data labels, explicit colors) are preserved — only defaults are
    overridden.
    """
    fig.update_layout(
        # ── Font ─────────────────────────────────────
        font=dict(family="Geist, Inter, system-ui, sans-serif", color="#E6EDF3"),
        title=dict(font=dict(size=15, color="#F1F3FC")),
        # ── Backgrounds (transparent — let cards show) ─
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        # ── Color sequence ───────────────────────────
        colorway=DATARA_COLORS,
        # ── Axes ──────────────────────────────────────
        xaxis=dict(
            gridcolor="#2A2F35",
            zerolinecolor="#44484F",
            tickfont=dict(size=11, color="#8B949E"),
            title=dict(font=dict(size=12, color="#E6EDF3")),
            showgrid=True,
            zeroline=False,
        ),
        yaxis=dict(
            gridcolor="#2A2F35",
            zerolinecolor="#44484F",
            tickfont=dict(size=11, color="#8B949E"),
            title=dict(font=dict(size=12, color="#E6EDF3")),
            showgrid=True,
            zeroline=False,
        ),
        # ── Legend ────────────────────────────────────
        legend=dict(
            font=dict(size=11, color="#E6EDF3"),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="#44484F",
        ),
        # ── Margins ──────────────────────────────────
        margin=dict(l=50, r=20, t=40, b=50),
        # ── Hover ────────────────────────────────────
        hovermode="closest",
        hoverlabel=dict(
            font=dict(size=12, color="#F1F3FC"),
            bordercolor="#44484F",
        ),
    )

    return fig
