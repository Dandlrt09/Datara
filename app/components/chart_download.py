"""
Chart component: renders a Plotly chart with download (PNG) and export options.
"""

from __future__ import annotations

from typing import Optional

import streamlit as st
import plotly.graph_objects as go

from services.export_service import ExportService


def render_chart_with_download(
    figure: go.Figure,
    timestamp: Optional[str] = None,
):
    """
    Render a Plotly chart with download buttons.

    Args:
        figure: Plotly Figure to render
        timestamp: Optional timestamp for filename
    """
    # Render chart
    st.plotly_chart(figure, width="stretch")

    # Download buttons
    col1, col2 = st.columns(2)

    with col1:
        # Export as PNG
        png_bytes = ExportService.chart_to_png(figure)
        if png_bytes:
            filename = f"grafico_{timestamp or 'chart'}.png"
            st.download_button(
                label="📥 Descargar PNG",
                data=png_bytes,
                file_name=filename,
                mime="image/png",
                width="stretch",
            )
        else:
            # Fallback: download HTML
            html = ExportService.chart_to_html(figure)
            st.download_button(
                label="📥 Descargar HTML",
                data=html,
                file_name=f"grafico_{timestamp or 'chart'}.html",
                mime="text/html",
                width="stretch",
            )

    with col2:
        # Export data as CSV if figure has data
        if figure.data:
            try:
                # Try to extract data from figure traces
                records = []
                for trace in figure.data:
                    if hasattr(trace, "x") and hasattr(trace, "y"):
                        x_vals = trace.x if trace.x else []
                        y_vals = trace.y if trace.y else []
                        name = trace.name or "series"
                        for i in range(max(len(x_vals), len(y_vals))):
                            records.append({
                                "etiqueta": x_vals[i] if i < len(x_vals) else "",
                                name: y_vals[i] if i < len(y_vals) else "",
                            })

                if records:
                    import pandas as pd
                    df = pd.DataFrame(records)
                    csv = df.to_csv(index=False).encode("utf-8-sig")
                    st.download_button(
                        label="📥 Datos del gráfico (CSV)",
                        data=csv,
                        file_name=f"datos_grafico_{timestamp or 'chart'}.csv",
                        mime="text/csv",
                        width="stretch",
                    )
            except Exception:
                pass  # Silently skip CSV export from figure
