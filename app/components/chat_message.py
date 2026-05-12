"""
Chat message component: renders individual chat bubbles for user and assistant.
"""

from __future__ import annotations

import streamlit as st


def render_message(role: str, content: str, index: int):
    """
    Render a single chat message bubble.

    Args:
        role: "user" or "assistant"
        content: Message text content
        index: Message index for unique keys
    """
    avatar = "🧑‍💻" if role == "user" else "🤖"

    with st.chat_message(role, avatar=avatar):
        st.markdown(content)


def render_error_message(error_text: str):
    """Render an error message in the chat."""
    st.error(f"❌ {error_text}")
