"""
Code Executor: orchestrates the LLM + Sandbox pipeline.

Takes a user question + loaded files → LLM generates code →
Sandbox executes code → Returns AnalysisResult with text, figure, or dataframe.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import pandas as pd

from models import AnalysisResult, FileData
from utils.prompts import build_context
from utils.sandbox import SafeExecutor
from services.llm_service import LLMService


def _sanitize_varname(filename: str) -> str:
    """Turn a filename into a valid Python variable name.

    Examples:
        Computers.csv  → df_computers
        my-data.csv    → df_my_data
        datos (1).xlsx → df_datos_1
    """
    stem = Path(filename).stem
    # Replace non-alphanumeric chars (except underscore) with underscore
    name = re.sub(r"[^a-zA-Z0-9_]", "_", stem)
    # Collapse multiple underscores
    name = re.sub(r"_+", "_", name)
    # Strip leading/trailing underscores
    name = name.strip("_")
    # Ensure it's not empty
    if not name:
        name = "data"
    return f"df_{name}"


class CodeExecutor:
    """
    Orchestrates the full analysis pipeline:
      1. Build context from files + question
      2. Call LLM to generate analysis code
      3. Execute code in sandbox
      4. Return structured result
    """

    def __init__(
        self,
        llm_service: LLMService,
        sandbox: Optional[SafeExecutor] = None,
    ):
        self.llm = llm_service
        self.sandbox = sandbox or SafeExecutor()

    @staticmethod
    def _build_dataframe_map(
        files: list[FileData],
    ) -> tuple[dict[str, "pd.DataFrame"], list[str]]:
        """Build a dict of {variable_name: DataFrame} + list of names for the prompt.

        Single file → exposed as both `df` (shortcut) and `df_{name}`.
        Multiple files → each gets `df_{name}_1`, `df_{name}_2`, etc.
        """
        df_map: dict[str, pd.DataFrame] = {}
        names: list[str] = []

        if not files:
            return df_map, names

        if len(files) == 1:
            varname = _sanitize_varname(files[0].filename)
            df_map["df"] = files[0].df
            df_map[varname] = files[0].df
            names = [varname]
        else:
            for i, f in enumerate(files, 1):
                base = _sanitize_varname(f.filename)
                varname = f"{base}_{i}" if len(files) > 1 else base
                df_map[varname] = f.df
                names.append(varname)
            # Also expose the first file as `df` for convenience
            first = names[0]
            df_map["df"] = df_map[first]

        return df_map, names

    def analyze(
        self,
        question: str,
        files: list[FileData],
        chat_history: list | None = None,
    ) -> AnalysisResult:
        """
        Run a full analysis cycle: LLM → code → execute → result.

        Args:
            question: User's natural language question
            files: Currently loaded data files
            chat_history: Previous messages for follow-up context

        Returns:
            AnalysisResult with text, optional figure/dataframe, or error
        """
        # Step 1: Build context (including conversation history)
        df_map, df_names = self._build_dataframe_map(files)
        context = build_context(files, question, df_names=df_names, chat_history=chat_history)

        # Step 2: Handle no files case
        if not files:
            return AnalysisResult(
                text="No hay archivos cargados. Primero subí un archivo CSV o Excel "
                     "para poder analizar los datos.",
                error="No files loaded",
            )

        # Step 3: Check LLM is configured
        if not self.llm.is_configured:
            return AnalysisResult(
                text="API key de Gemini no configurada. Andá a Settings "
                     "y cargá tu API key de https://aistudio.google.com/apikey",
                error="API key not configured",
            )

        # Step 4: Get code from LLM
        try:
            code, text, raw = self.llm.generate_code(context)
        except (RuntimeError, ConnectionError) as e:
            return AnalysisResult(
                text=str(e),
                error=str(e),
            )

        if not code:
            # LLM responded with text only (no code needed)
            return AnalysisResult(text=text or raw)

        # Step 5: Execute code in sandbox (with dataframes injected)
        success, error_msg = self.sandbox.execute(code, dataframes=df_map)

        # Step 6: Build result
        result = AnalysisResult(
            text="",
            figure=self.sandbox.last_figure,
            dataframe=self.sandbox.last_dataframe,
            code_executed=code,
        )

        if not success:
            # If code execution failed, try ONE retry with error feedback
            retry_context = (
                f"{context}\n\n"
                f"El código anterior produjo este error:\n{error_msg}\n\n"
                f"Corregí el error y generá código nuevo."
            )
            try:
                code2, text2, _ = self.llm.generate_code(retry_context)
                if code2:
                    success2, error_msg2 = self.sandbox.execute(code2, dataframes=df_map)
                    if success2:
                        text_parts2 = []
                        if self.sandbox.last_text:
                            text_parts2.append(self.sandbox.last_text)
                        if self.sandbox.last_figure is not None:
                            text_parts2.append("Gráfico generado correctamente.")
                        if self.sandbox.last_dataframe is not None:
                            rows = len(self.sandbox.last_dataframe)
                            text_parts2.append(f"Tabla generada con {rows} filas.")
                        if text2 and not self.sandbox.last_text:
                            text_parts2.append(text2)
                        result = AnalysisResult(
                            text=" ".join(text_parts2) if text_parts2 else "Análisis completado.",
                            figure=self.sandbox.last_figure,
                            dataframe=self.sandbox.last_dataframe,
                            code_executed=code2,
                        )
                        return result
            except Exception:
                pass

            # Both attempts failed
            result.text = (
                "No pude generar un análisis válido para esta pregunta. "
                "Probá reformularla de otra manera.\n\n"
                f"Error: {error_msg}"
            )
            result.error = error_msg
            return result

        # Build descriptive text based on what the code generated
        text_parts = []

        # If code set result_text, use it as the primary text
        if self.sandbox.last_text:
            text_parts.append(self.sandbox.last_text)

        if result.has_figure:
            text_parts.append("Gráfico generado correctamente.")
        if result.has_dataframe:
            rows = len(self.sandbox.last_dataframe) if self.sandbox.last_dataframe is not None else 0
            text_parts.append(f"Tabla generada con {rows} filas.")

        # Only use LLM's non-code text if code didn't already set result_text
        if text and not self.sandbox.last_text:
            text_parts.append(text)

        result.text = " ".join(text_parts) if text_parts else "Análisis completado."
        return result
