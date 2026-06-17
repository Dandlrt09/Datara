"""
Upload page: file upload, validation, and data preview.
Supports CSV, Excel with sheet selection, and duplicate file handling.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from services.file_service import FileService
from app.components.data_preview import render_preview


def show_upload_page():
    """Render the file upload page."""
    st.title("📁 Cargar Datos")

    st.markdown(
        """
        Subí un archivo **CSV**, **Excel (.xlsx)**, **JSON** o **TSV** para empezar.
        Podés cargar múltiples archivos y después preguntarle a la IA sobre ellos.
        """
    )

    # Init pending state
    if "pending_excel" not in st.session_state:
        st.session_state.pending_excel = {}
    if "pending_duplicates" not in st.session_state:
        st.session_state.pending_duplicates = {}

    # ─── Handle pending duplicate dialogs ────────────────────────
    _handle_pending_duplicates()

    # ─── Handle pending Excel sheet selection ────────────────────
    if st.session_state.pending_excel:
        _handle_pending_excel()

    # ─── File uploader ──────────────────────────────────────────
    uploaded_files = st.file_uploader(
        "Seleccioná un archivo",
        type=["csv", "xlsx", "json", "tsv"],
        accept_multiple_files=True,
        help="Formatos soportados: CSV, Excel (.xlsx), JSON y TSV. Máx 200 MB por archivo.",
    )

    if not uploaded_files:
        if st.session_state.file_service.file_count == 0:
            st.info("👆 Subí un archivo para empezar.")
        else:
            _show_loaded_files()
        return

    file_service: FileService = st.session_state.file_service

    for uploaded_file in uploaded_files:
        filename = uploaded_file.name
        content = uploaded_file.getvalue()
        ext = Path(filename).suffix.lower()

        # ─── Detect duplicates BEFORE parsing ──────────────────
        if filename in file_service.get_filenames():
            st.session_state.pending_duplicates[filename] = content
            continue

        # ─── Validate first ────────────────────────────────────
        from utils.validators import validate_file
        validation = validate_file(filename, len(content))
        if not validation.valid:
            st.error(f"❌ **{filename}**: {validation.error_message}")
            continue

        # ─── Excel: check sheets before loading ────────────────
        if ext == ".xlsx":
            sheets = file_service.get_excel_sheets(content)
            if len(sheets) > 1:
                st.session_state.pending_excel[filename] = {
                    "content": content,
                    "sheets": sheets,
                }
                continue

        # ─── Parse and add ─────────────────────────────────────
        _parse_and_add_file(file_service, filename, content, ext)

    # Show all loaded files
    _show_loaded_files()


def _parse_and_add_file(
    file_service: FileService,
    filename: str,
    content: bytes,
    ext: str,
    sheet_name: str = "",
):
    """Parse a file and add it to the service. Shows success/error."""
    try:
        if ext == ".csv":
            filedata = file_service.parse_csv(filename, content)
        elif ext == ".xlsx":
            filedata = file_service.parse_excel(filename, content, sheet_name=sheet_name)
        elif ext == ".json":
            filedata = file_service.parse_json(filename, content)
        elif ext == ".tsv":
            filedata = file_service.parse_tsv(filename, content)
        else:
            st.error(f"Formato no soportado: {ext}")
            return

        file_service.add_file(filedata)
        st.success(
            f"✅ **{filedata.display_name}** cargado correctamente — "
            f"{filedata.rows} filas × {filedata.columns} columnas"
        )
    except Exception as e:
        st.error(f"❌ **{filename}**: {e}")


def _handle_pending_excel():
    """Show sheet selector for Excel files with multiple sheets."""
    pending = st.session_state.pending_excel
    to_remove = []

    file_service: FileService = st.session_state.file_service

    for filename, data in pending.items():
        if filename in file_service.get_filenames():
            to_remove.append(filename)
            continue

        st.info(f"📄 **{filename}** tiene múltiples hojas. Seleccioná cuál querés cargar:")

        selected_sheet = st.selectbox(
            "Hojas disponibles",
            options=data["sheets"],
            key=f"sheet_{filename}",
        )

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button(f"✅ Cargar '{selected_sheet}'", key=f"load_{filename}"):
                _parse_and_add_file(
                    file_service, filename, data["content"], ".xlsx",
                    sheet_name=selected_sheet,
                )
                to_remove.append(filename)
                st.rerun()
        with col2:
            if st.button("❌ Descartar", key=f"skip_{filename}"):
                to_remove.append(filename)
                st.rerun()

    for name in to_remove:
        pending.pop(name, None)


def _handle_pending_duplicates():
    """Show replace/keep dialog for duplicate filenames."""
    pending = st.session_state.pending_duplicates
    if not pending:
        return

    file_service: FileService = st.session_state.file_service
    to_remove = []

    for filename, content in pending.items():
        ext = Path(filename).suffix.lower()
        st.warning(f"⚠️ **'{filename}'** ya está cargado. ¿Qué querés hacer?")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🔄 Reemplazar", key=f"replace_{filename}"):
                # Remove old, add new
                file_service.remove_file(filename)
                _parse_and_add_file(file_service, filename, content, ext)
                to_remove.append(filename)
                st.rerun()
        with col2:
            if st.button("📄 Mantener ambos", key=f"keep_{filename}"):
                # Save with a different name
                base = Path(filename)
                counter = 2
                while f"{base.stem} ({counter}){base.suffix}" in file_service.get_filenames():
                    counter += 1
                alt_name = f"{base.stem} ({counter}){base.suffix}"
                _parse_and_add_file(file_service, alt_name, content, ext)
                to_remove.append(filename)
                st.rerun()

    for name in to_remove:
        pending.pop(name, None)


def _show_loaded_files():
    """Display all currently loaded files with previews."""
    file_service: FileService = st.session_state.file_service

    if file_service.file_count == 0:
        return

    st.divider()
    st.subheader(f"Archivos cargados ({file_service.file_count})")

    for fdata in file_service.list_files():
        with st.expander(
            f"📄 {fdata.display_name} "
            f"({fdata.rows} filas × {fdata.columns} columnas)",
            expanded=True,
        ):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.caption(f"Tamaño: {fdata.size_bytes / 1024:.1f} KB")
                if fdata.sheet_name:
                    st.caption(f"Hoja: {fdata.sheet_name}")
                st.caption(f"Tipos: {', '.join(f'{c}: {t}' for c, t in list(fdata.dtypes.items())[:5])}")

            with col2:
                if st.button(
                    "🗑️ Eliminar",
                    key=f"remove_{fdata.display_name}",
                    width="stretch",
                ):
                    file_service.remove_file(fdata.display_name)
                    st.rerun()

            # Data preview
            render_preview(fdata.df, key=f"preview_{fdata.display_name}")
