"""
Sidebar component: display and manage loaded files.
"""

from __future__ import annotations

import streamlit as st

from services.file_service import FileService


def render_file_list():
    """Render the file list in the sidebar with remove buttons."""
    file_service: FileService = st.session_state.file_service

    if file_service.file_count == 0:
        st.sidebar.caption("No hay archivos cargados.")
        return

    st.sidebar.caption(f"📁 Archivos ({file_service.file_count})")

    for fdata in file_service.list_files():
        col1, col2 = st.sidebar.columns([3, 1])
        with col1:
            st.caption(f"📄 {fdata.display_name}")
            st.caption(f"   {fdata.rows} filas", help=f"{fdata.columns} columnas")
        with col2:
            if st.button("✕", key=f"remove_{fdata.display_name}", help="Eliminar"):
                file_service.remove_file(fdata.display_name)
                st.rerun()
