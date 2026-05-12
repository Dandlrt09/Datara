"""
Data preview component: renders a DataFrame with pagination and column info.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
import streamlit as st


def render_preview(
    df: pd.DataFrame,
    key: str = "preview",
    default_rows: int = 10,
):
    """
    Render an interactive preview of a DataFrame.

    Args:
        df: DataFrame to preview
        key: Unique key for Streamlit state
        default_rows: Number of rows to show by default
    """
    col_info_col, preview_col = st.columns([1, 3])

    with col_info_col:
        st.markdown("**Info**")
        st.caption(f"📊 {len(df)} filas × {len(df.columns)} columnas")

        # Column info
        with st.expander("Columnas", expanded=False):
            for col in df.columns:
                dtype = df[col].dtype
                nulls = df[col].isna().sum()
                st.caption(f"**{col}**")
                st.caption(f"  Tipo: {dtype}")
                if nulls > 0:
                    st.caption(f"  Vacíos: {nulls}")

        # Pagination
        rows_per_page = st.selectbox(
            "Filas por página",
            options=[5, 10, 25, 50, 100],
            index=1,
            key=f"{key}_rows",
        )

    with preview_col:
        st.dataframe(
            df,
            width="stretch",
            height=min(400, 35 * rows_per_page + 50),
        )


def render_column_selector(
    df: pd.DataFrame,
    key: str = "col_selector",
) -> list[str]:
    """
    Render a multi-select column chooser.

    Returns:
        List of selected column names
    """
    all_cols = df.columns.tolist()
    selected = st.multiselect(
        "Seleccioná columnas",
        options=all_cols,
        default=all_cols,
        key=key,
    )
    return selected or all_cols
