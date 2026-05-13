"""
Chat page: natural language Q&A with AI about loaded data.
Supports follow-up questions, chart export, and conversation export.
"""

from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
import streamlit as st
import plotly.io as pio

from models import ChatMessage, AnalysisResult
from services.code_executor import CodeExecutor
from services.export_service import ExportService
from app.components.chart_download import render_chart_with_download
from app.components.dashboard import render_dashboard
from app.components.chart_builder import render_chart_builder


def show_chat_page():
    """Render the chat page."""
    st.title("💬 Chat con IA")

    # Check if there are loaded files
    file_service = st.session_state.file_service
    if file_service.file_count == 0:
        st.warning(
            "⚠️ No hay archivos cargados. "
            "Andá a **Cargar Datos** y subí un archivo primero."
        )
        return

    # Show active files info + message count
    active_files = ", ".join(file_service.get_filenames())
    msg_count = len(st.session_state.chat_messages)
    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption(f"📄 Datos activos: {active_files}")
    with col2:
        st.caption(f"💬 Mensajes: {msg_count}")

    # ─── Export conversation button (Fix 4: EX-S3) ─────────────
    if st.session_state.chat_messages:
        if st.button("📥 Exportar conversación", width="stretch"):
            chat_for_export = [
                m for m in st.session_state.chat_messages
                if m.role in ("user", "assistant")
            ]
            text = ExportService.conversation_to_text(chat_for_export)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                label="📥 Descargar .txt",
                data=text.encode("utf-8-sig"),
                file_name=f"conversacion_{timestamp}.txt",
                mime="text/plain",
            )

    # ─── Dashboard (accumulated charts + KPIs) ───────────────────
    render_dashboard(file_service)

    # ─── Display chat history ───────────────────────────────────
    chat_container = st.container()
    with chat_container:
        for i, msg in enumerate(st.session_state.chat_messages):
            with st.chat_message(msg.role):
                st.markdown(msg.content)

                # Render figure if present
                if msg.figure_json:
                    try:
                        fig = pio.from_json(msg.figure_json)
                        render_chart_with_download(fig, msg.timestamp)
                    except Exception:
                        st.error("No se pudo renderizar el gráfico.")

                # Render dataframe if present
                if msg.dataframe_json:
                    try:
                        df = pd.read_json(msg.dataframe_json, orient="split")
                        display_df = df.head(100)
                        st.dataframe(display_df, width="stretch")
                        if len(df) > 100:
                            st.caption(f"📊 Mostrando primeras 100 filas de {len(df)} totales")
                    except Exception:
                        st.error("No se pudo renderizar la tabla guardada.")

                # Fix 5 (REQ-EX-03): copy/download individual response
                if msg.role == "assistant" and msg.content and not msg.error:
                    export_text = msg.to_export_text(i + 1)
                    st.download_button(
                        label="📋 Copiar respuesta",
                        data=export_text.encode("utf-8-sig"),
                        file_name=f"respuesta_{i+1}.txt",
                        mime="text/plain",
                        key=f"export_msg_{i}",
                    )

    # ─── Chart Builder (collapsible) ─────────────────────────────
    with st.expander("📊 Constructor de Gráficos", expanded=False):
        render_chart_builder(file_service)

    # ─── Chat input ────────────────────────────────────────────
    question = st.chat_input("Escribí tu pregunta sobre los datos...")

    if not question:
        return

    # Add user message
    user_msg = ChatMessage(role="user", content=question)
    st.session_state.chat_messages.append(user_msg)

    with st.chat_message("user"):
        st.markdown(question)

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("🤔 Analizando datos..."):
            executor: CodeExecutor = st.session_state.code_executor
            files = file_service.list_files()
            # Fix 2 (DC-S2): pass chat history for follow-up context
            history = st.session_state.chat_messages[:-1]  # Exclude current user msg
            result: AnalysisResult = executor.analyze(
                question, files, chat_history=history
            )

        # Initialize variables for all branches
        fig_json = None
        df_json = None

        if result.error and not result.text:
            st.error(f"❌ {result.text}")
        elif result.error:
            st.warning(result.text)
        else:
            # Show any text response
            if result.text:
                st.markdown(result.text)

            # Show figure if generated
            if result.has_figure:
                render_chart_with_download(result.figure)
                fig_json = pio.to_json(result.figure)

            # Show dataframe if generated
            if result.has_dataframe:
                df = result.dataframe
                # Bug fix: limit to 100 rows for display
                display_df = df.head(100)
                st.dataframe(display_df, width="stretch")
                if len(df) > 100:
                    st.caption(f"📊 Mostrando primeras 100 filas de {len(df)} totales")
                # Export CSV for this result
                csv = df.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    label="📥 Descargar CSV",
                    data=csv,
                    file_name="analisis_resultado.csv",
                    mime="text/csv",
                )
                df_json = df.to_json(orient="split", date_format="iso")

        # Save assistant message
        assistant_msg = ChatMessage(
            role="assistant",
            content=result.text or "Análisis completado.",
            figure_json=fig_json,
            dataframe_json=df_json,
            error=bool(result.error),
        )
        st.session_state.chat_messages.append(assistant_msg)
