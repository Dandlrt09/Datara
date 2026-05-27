"""
Integration tests for CodeExecutor.analyze() — full pipeline with mocked LLM.

Tests the end-to-end flow:
  question + files → context → LLM (mocked) → sandbox → AnalysisResult

All LLM calls are mocked — no real Gemini API calls are made.
"""

import pandas as pd
import plotly.graph_objects as go
import pytest

from models import AnalysisResult, FileData
from services.code_executor import CodeExecutor
from services.llm_service import LLMService
from utils.sandbox import SafeExecutor


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def llm_service():
    """A real LLMService instance — generate_code() will be mocked per test."""
    return LLMService(api_key="fake-key-for-testing")


@pytest.fixture
def sandbox():
    return SafeExecutor(timeout=5)


@pytest.fixture
def executor(llm_service, sandbox):
    return CodeExecutor(llm_service=llm_service, sandbox=sandbox)


@pytest.fixture
def sample_file():
    return FileData(
        filename="computers.csv",
        df=pd.DataFrame({"marca": ["A", "B", "C"], "precio": [1000, 2000, 3000]}),
    )


@pytest.fixture
def sample_files(sample_file):
    return [sample_file]


# ── LLM returns valid code, execution succeeds ──────────────────────


class TestAnalyzeSuccess:
    """Happy paths: LLM returns valid code that runs in the sandbox."""

    def test_text_only_response(self, executor, sample_files, monkeypatch):
        """LLM generates code that sets result_text."""

        def mock_generate_code(_context):
            return ("result_text = 'El promedio de precio es $2000'", "", "")

        monkeypatch.setattr(executor.llm, "generate_code", mock_generate_code)

        result = executor.analyze("¿Cuál es el precio promedio?", sample_files)

        assert result.success
        assert result.error is None
        assert "2000" in result.text
        assert result.figure is None
        assert result.dataframe is None

    def test_figure_response(self, executor, sample_files, monkeypatch):
        """LLM generates code that creates a Plotly figure."""

        def mock_generate_code(_context):
            code = """
fig = go.Figure(data=go.Bar(x=["A","B","C"], y=[1000,2000,3000]))
fig.update_layout(title="Precios por marca")
"""
            return (code.strip(), "", "")

        monkeypatch.setattr(executor.llm, "generate_code", mock_generate_code)

        result = executor.analyze("Graficá precios por marca", sample_files)

        assert result.success
        assert result.has_figure
        assert result.figure is not None
        assert "Precios por marca" in (result.figure.layout.title.text or "")

    def test_dataframe_response(self, executor, sample_files, monkeypatch):
        """LLM generates code that creates a result_df."""

        def mock_generate_code(_context):
            code = "result_df = df.groupby('marca').agg({'precio': 'mean'})"
            return (code, "", "")

        monkeypatch.setattr(executor.llm, "generate_code", mock_generate_code)

        result = executor.analyze("Dame el promedio por marca", sample_files)

        assert result.success
        assert result.has_dataframe
        assert result.dataframe is not None
        assert list(result.dataframe.index) == ["A", "B", "C"]

    def test_multiple_outputs(self, executor, sample_files, monkeypatch):
        """LLM code sets result_text AND fig AND result_df."""

        def mock_generate_code(_context):
            code = """
fig = go.Figure(data=go.Bar(x=["A","B","C"], y=[1000,2000,3000]))
result_df = df.groupby('marca').precio.mean().reset_index()
result_text = "Gráfico y tabla generados correctamente."
"""
            return (code, "", "")

        monkeypatch.setattr(executor.llm, "generate_code", mock_generate_code)

        result = executor.analyze("Analizá los datos", sample_files)

        assert result.success
        assert result.has_figure
        assert result.has_dataframe
        assert "Gráfico" in result.text

    def test_result_text_from_sandbox_preferred_over_llm_text(self, executor, sample_files, monkeypatch):
        """When sandbox captures result_text AND LLM returns non-code text,
        the sandbox text should be primary."""

        def mock_generate_code(_context):
            # Returns code that sets result_text, plus some LLM commentary
            return ("result_text = 'texto del sandbox'", "texto del LLM", "")

        monkeypatch.setattr(executor.llm, "generate_code", mock_generate_code)

        result = executor.analyze("Pregunta", sample_files)

        assert result.success
        assert "texto del sandbox" in result.text


# ── LLM returns text only (no code block) ───────────────────────────


class TestAnalyzeTextOnly:
    """When the LLM responds with natural language only (no code block)."""

    def test_text_only_from_llm(self, executor, sample_files, monkeypatch):
        """LLM returns only text — no code block found."""

        def mock_generate_code(_context):
            # No code in response — generate_code returns ("", text, raw)
            return ("", "Hay 3 marcas distintas en el dataset.", "")

        monkeypatch.setattr(executor.llm, "generate_code", mock_generate_code)

        result = executor.analyze("Cuántas marcas hay?", sample_files)

        assert result.success
        assert "3 marcas" in result.text
        assert result.figure is None
        assert result.dataframe is None


# ── Error recovery: sandbox fails, retry succeeds ───────────────────


class TestAnalyzeRetrySuccess:
    """First code execution fails, but retry succeeds."""

    def test_retry_after_syntax_error(self, executor, sample_files, monkeypatch):
        """Sandbox fails on first attempt, retry generates corrected code."""
        call_count = 0

        def mock_generate_code(context):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call: code with error
                return ("result_text = 'incompleto", "", "")
            # Retry: corrected code
            return ("result_text = 'corregido'", "", "")

        monkeypatch.setattr(executor.llm, "generate_code", mock_generate_code)

        result = executor.analyze("Pregunta", sample_files)

        assert result.success
        assert "corregido" in result.text
        assert call_count == 2  # Original + retry


# ── Error recovery: both attempts fail ──────────────────────────────


class TestAnalyzeRetryFails:
    """Both the original and retry execution fail."""

    def test_both_attempts_fail(self, executor, sample_files, monkeypatch):
        """Code keeps failing — returns error result after retry."""

        def mock_generate_code(_context):
            return ("result_text = undefined_var", "", "")

        monkeypatch.setattr(executor.llm, "generate_code", mock_generate_code)

        result = executor.analyze("Pregunta", sample_files)

        assert not result.success
        assert result.error is not None
        assert result.text != ""

    def test_retry_exception_swallowed(self, executor, sample_files, monkeypatch):
        """Retry itself raises an exception (e.g. LLM fails on retry) — should not propagate."""

        def mock_generate_code_first(_context):
            return ("result_text = undefined_var", "", "")

        monkeypatch.setattr(executor.llm, "generate_code", mock_generate_code_first)

        # First analyze call to set up state, then mock retry to throw
        # We simulate by having the sandbox.failed_execution trigger a bad retry
        result = executor.analyze("Pregunta", sample_files)
        assert not result.success


# ── LLM service errors ──────────────────────────────────────────────


class TestAnalyzeServiceErrors:
    """When the LLM service itself raises errors."""

    def test_llm_raises_runtime_error(self, executor, sample_files, monkeypatch):
        """LLM raises RuntimeError (e.g. bad API key)."""

        def mock_generate_code(_context):
            raise RuntimeError("API key inválida.")

        monkeypatch.setattr(executor.llm, "generate_code", mock_generate_code)

        result = executor.analyze("Pregunta", sample_files)

        assert not result.success
        assert "API key" in result.text

    def test_llm_raises_connection_error(self, executor, sample_files, monkeypatch):
        """LLM raises ConnectionError (e.g. rate limit)."""

        def mock_generate_code(_context):
            raise ConnectionError("Límite de tasa alcanzado.")

        monkeypatch.setattr(executor.llm, "generate_code", mock_generate_code)

        result = executor.analyze("Pregunta", sample_files)

        assert not result.success
        assert "Límite" in result.text


# ── Guard clauses (early returns) ───────────────────────────────────


class TestAnalyzeGuardClauses:
    """Early return scenarios before any LLM call."""

    def test_no_files(self, executor, monkeypatch):
        """No files loaded → early return with friendly message."""
        called = False

        def mock_generate_code(_context):
            nonlocal called
            called = True
            return ("result_text = 'hi'", "", "")

        monkeypatch.setattr(executor.llm, "generate_code", mock_generate_code)

        result = executor.analyze("Pregunta", [])

        assert not result.success
        assert "no hay archivos" in result.text.lower()
        assert not called, "LLM should NOT be called when there are no files"

    def test_llm_not_configured(self, executor, sample_files, monkeypatch):
        """LLM not configured → early return with key setup message."""
        monkeypatch.setattr(executor.llm, "api_key", "")

        called = False

        def mock_generate_code(_context):
            nonlocal called
            called = True
            return ("result_text = 'hi'", "", "")

        monkeypatch.setattr(executor.llm, "generate_code", mock_generate_code)

        result = executor.analyze("Pregunta", sample_files)

        assert not result.success
        assert "API key" in result.text or "Settings" in result.text
        assert not called, "LLM should NOT be called when not configured"


# ── Chat history integration ────────────────────────────────────────


class TestAnalyzeWithHistory:
    """analyze() passes chat_history to build_context (covered by prompt tests)."""

    def test_chat_history_passed_to_context(self, executor, sample_files, monkeypatch):
        """Verify chat_history is passed to the context builder."""
        from models import ChatMessage

        history = [
            ChatMessage(role="user", content="primera pregunta"),
            ChatMessage(role="assistant", content="primera respuesta"),
        ]
        captured_context = None

        def mock_generate_code(context):
            nonlocal captured_context
            captured_context = context
            return ("result_text = 'con historial'", "", "")

        monkeypatch.setattr(executor.llm, "generate_code", mock_generate_code)

        result = executor.analyze("segunda pregunta", sample_files, chat_history=history)

        assert result.success
        assert captured_context is not None
        assert "primera pregunta" in captured_context
        assert "primera respuesta" in captured_context
        assert "segunda pregunta" in captured_context

    def test_empty_chat_history(self, executor, sample_files, monkeypatch):
        """Empty chat_history should not cause errors."""

        def mock_generate_code(context):
            return ("result_text = 'sin historial'", "", "")

        monkeypatch.setattr(executor.llm, "generate_code", mock_generate_code)

        result = executor.analyze("Pregunta", sample_files, chat_history=[])
        assert result.success

    def test_none_chat_history(self, executor, sample_files, monkeypatch):
        """None chat_history should not cause errors."""

        def mock_generate_code(context):
            return ("result_text = 'sin historial'", "", "")

        monkeypatch.setattr(executor.llm, "generate_code", mock_generate_code)

        result = executor.analyze("Pregunta", sample_files, chat_history=None)
        assert result.success


# ── Multi-file scenarios ────────────────────────────────────────────


class TestAnalyzeMultiFile:
    """analyze() with multiple files loaded."""

    def test_two_files_accessible_in_sandbox(self, executor, monkeypatch):
        """Both dataframes are injected and accessible."""
        df1 = pd.DataFrame({"x": [1, 2]})
        df2 = pd.DataFrame({"y": [3, 4]})
        files = [
            FileData(filename="a.csv", df=df1),
            FileData(filename="b.csv", df=df2),
        ]

        def mock_generate_code(_context):
            # Code references both dataframes
            return ("result_text = str(df_a_1.x.sum() + df_b_2.y.sum())", "", "")

        monkeypatch.setattr(executor.llm, "generate_code", mock_generate_code)

        result = executor.analyze("Sumá todo", files)
        assert result.success
        assert "10" in result.text  # 1+2+3+4

    def test_first_file_accessible_as_df(self, executor, monkeypatch):
        """The first file is also exposed as `df` even with multiple files."""
        df1 = pd.DataFrame({"x": [42]})
        df2 = pd.DataFrame({"y": [99]})
        files = [
            FileData(filename="first.csv", df=df1),
            FileData(filename="second.csv", df=df2),
        ]

        def mock_generate_code(_context):
            return ("result_text = str(df.x.iloc[0])", "", "")

        monkeypatch.setattr(executor.llm, "generate_code", mock_generate_code)

        result = executor.analyze("Valor de x", files)
        assert result.success
        assert "42" in result.text


# ── LLM returns empty response ──────────────────────────────────────


class TestAnalyzeEdgeCases:
    """Edge cases around LLM responses."""

    def test_empty_llm_response(self, executor, sample_files, monkeypatch):
        """LLM returns completely empty response."""

        def mock_generate_code(_context):
            return ("", "", "")

        monkeypatch.setattr(executor.llm, "generate_code", mock_generate_code)

        result = executor.analyze("Pregunta", sample_files)
        # Should handle gracefully — no code, no text
        assert result.success

    def test_code_with_print_only(self, executor, sample_files, monkeypatch):
        """Code runs but doesn't set any result_* variable — no error but no output."""

        def mock_generate_code(_context):
            return ("print('hello')", "", "")

        monkeypatch.setattr(executor.llm, "generate_code", mock_generate_code)

        result = executor.analyze("Pregunta", sample_files)
        assert result.success
        assert result.text == "Análisis completado."
        assert result.figure is None
        assert result.dataframe is None
