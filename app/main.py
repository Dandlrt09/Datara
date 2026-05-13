"""
Datara — MVP
Streamlit app for uploading data files and analyzing them with AI.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure project root is in sys.path (needed when running streamlit from subdir)
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Load .env file from project root
from dotenv import load_dotenv
_dotenv_path = Path(_project_root) / ".env"
if _dotenv_path.exists():
    load_dotenv(_dotenv_path)
else:
    load_dotenv()  # fallback to default

import streamlit as st

from services.file_service import FileService
from services.llm_service import LLMService
from services.code_executor import CodeExecutor
from utils.sandbox import SafeExecutor

# ─── Page config — MUST be first Streamlit command ────────────────

st.set_page_config(
    page_title="Datara",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Session State Initialization ─────────────────────────────────

def init_session_state():
    """Initialize all session state variables if they don't exist."""
    if "file_service" not in st.session_state:
        st.session_state.file_service = FileService()
    if "llm_service" not in st.session_state:
        st.session_state.llm_service = LLMService(
            api_key=os.getenv("GEMINI_API_KEY", ""),
            model=os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash"),
        )
    if "code_executor" not in st.session_state:
        st.session_state.code_executor = CodeExecutor(
            llm_service=st.session_state.llm_service,
            sandbox=SafeExecutor(),
        )
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "dashboard_items" not in st.session_state:
        st.session_state.dashboard_items = []
    if "dashboard_filters" not in st.session_state:
        st.session_state.dashboard_filters = {"columns": []}
    if "page" not in st.session_state:
        st.session_state.page = "Upload"


init_session_state()

# ─── Sidebar ──────────────────────────────────────────────────────

with st.sidebar:
    st.title("📊 Datara")

    st.divider()

    # Navigation
    if st.button(
        "📁 Cargar Datos",
        width="stretch",
        type="primary" if st.session_state.page == "Upload" else "secondary",
    ):
        st.session_state.page = "Upload"
        st.rerun()

    if st.button(
        "💬 Chat con IA",
        width="stretch",
        type="primary" if st.session_state.page == "Chat" else "secondary",
    ):
        st.session_state.page = "Chat"
        st.rerun()

    if st.button(
        "⚙️ Settings",
        width="stretch",
        type="primary" if st.session_state.page == "Settings" else "secondary",
    ):
        st.session_state.page = "Settings"
        st.rerun()

    st.divider()

    # File info in sidebar
    file_count = st.session_state.file_service.file_count
    st.caption(f"📁 Archivos: {file_count}")
    if file_count > 0:
        for fname in st.session_state.file_service.get_filenames():
            st.caption(f"  📄 {fname}")

    # Chat message count
    msg_count = len(st.session_state.chat_messages)
    st.caption(f"💬 Mensajes: {msg_count}")

    # Current provider info
    st.caption(f"⚡ {st.session_state.llm_service.provider_info}")

    st.divider()
    st.caption("v0.1 — MVP")

# ─── Page Router ──────────────────────────────────────────────────

def main():
    page = st.session_state.get("page", "Upload")

    if page == "Upload":
        from app.views.upload import show_upload_page
        show_upload_page()
    elif page == "Chat":
        from app.views.chat import show_chat_page
        show_chat_page()
    elif page == "Settings":
        from app.views.settings import show_settings_page
        show_settings_page()


if __name__ == "__main__":
    main()
