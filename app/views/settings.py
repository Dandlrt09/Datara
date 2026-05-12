"""
Settings page: API key config, model selection, session management.

Now Gemini-only. All Groq references removed.
"""

from __future__ import annotations

import os

import streamlit as st

from services.llm_service import LLMService


def show_settings_page():
    """Render the settings page."""
    st.title("⚙️ Settings")

    llm: LLMService = st.session_state.llm_service

    # ─── Gemini Settings ────────────────────────────────────────────

    st.subheader("🌟 Gemini — Configuración")

    st.info(
        "💡 **Gemini es el proveedor de IA.**\n\n"
        "Sacá tu API key gratis en https://aistudio.google.com/apikey\n"
        "El free tier incluye 60 requests/minuto sin costo."
    )

    current_key = llm.api_key
    masked_key = (
        current_key[:8] + "..." + current_key[-4:]
        if current_key and len(current_key) > 12
        else ""
    )

    if current_key and "your-" not in current_key:
        st.success(f"✅ Gemini configurado: {masked_key}")
    else:
        st.warning("⚠️ API key de Gemini no configurada.")

    api_key = st.text_input(
        "GEMINI_API_KEY",
        type="password",
        value=current_key if current_key and "your-" not in current_key else "",
        placeholder="AIzaxxxxxxxxxxxx",
        help="Obtené tu key gratis en https://aistudio.google.com/apikey",
        key="gemini_key_input",
    )

    gemini_models = [
        "models/gemini-2.5-flash",
        "models/gemini-2.0-flash",
        "models/gemini-2.0-flash-lite",
    ]
    model = st.selectbox(
        "Modelo Gemini",
        options=gemini_models,
        index=gemini_models.index(
            llm.model if llm.model in gemini_models else "models/gemini-2.5-flash"
        ),
        key="gemini_model_input",
    )

    # ─── Apply ──────────────────────────────────────────────────────
    if st.button("Aplicar cambios", type="primary", width="stretch"):
        _apply_settings(llm, api_key, model)
        st.rerun()

    # ─── Session Management ───────────────────────────────────────
    st.divider()
    st.subheader("🔄 Sesión")

    st.caption(
        "Esto borra todos los archivos cargados y el historial de chat. "
        "No se puede deshacer."
    )

    if st.button(
        "🗑️ Nueva sesión",
        type="secondary",
        width="stretch",
    ):
        st.session_state.file_service.clear_all()
        st.session_state.chat_messages = []
        st.session_state.page = "Upload"
        st.success("✅ Sesión reiniciada.")
        st.rerun()

    # ─── Info ─────────────────────────────────────────────────────
    st.divider()
    st.subheader("ℹ️ Info")

    st.markdown(
        f"""
        **Datara** v0.1 — MVP

        **Stack**:
        - App: Streamlit
        - Datos: Pandas + OpenPyXL
        - Gráficos: Plotly
        - IA: {llm.provider_info}

        **Límites actuales**:
        - Máx 200 MB por archivo
        - Los datos se pierden al cerrar el navegador
        """
    )


def _apply_settings(llm: LLMService, api_key: str, model: str):
    """Apply Gemini settings."""
    os.environ["GEMINI_API_KEY"] = api_key
    os.environ["GEMINI_MODEL"] = model

    # Rebuild the LLM service with new settings
    st.session_state.llm_service = LLMService(api_key=api_key, model=model)

    # Also rebuild the code executor with the new LLM
    from services.code_executor import CodeExecutor
    from utils.sandbox import SafeExecutor
    st.session_state.code_executor = CodeExecutor(
        llm_service=st.session_state.llm_service,
        sandbox=SafeExecutor(),
    )

    st.success(f"✅ Configuración actualizada: Gemini ({model})")
