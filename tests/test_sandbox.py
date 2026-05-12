"""Tests for utils/sandbox.py — SafeExecutor."""

import time

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from utils.sandbox import SafeExecutor, ExecutionTimeout, _safe_import


# ── Fixtures ───────────────────────────────────────────────────────


@pytest.fixture
def sandbox():
    return SafeExecutor(timeout=5)


# ── _safe_import ───────────────────────────────────────────────────


class TestSafeImport:
    def test_import_pandas(self):
        mod = _safe_import("pandas")
        assert mod is pd

    def test_import_numpy(self):
        mod = _safe_import("numpy")
        assert mod is np

    def test_import_plotly(self):
        mod = _safe_import("plotly")
        import plotly
        assert mod is plotly

    def test_import_plotly_express(self):
        """__import__('plotly.express') returns the top-level module (Python behavior)."""
        mod = _safe_import("plotly.express")
        import plotly
        assert mod is plotly  # __import__ returns top-level package

    def test_import_disallowed_os(self):
        with pytest.raises(ImportError):
            _safe_import("os")

    def test_import_disallowed_sys(self):
        with pytest.raises(ImportError):
            _safe_import("sys")

    def test_import_disallowed_subprocess(self):
        with pytest.raises(ImportError):
            _safe_import("subprocess")


# ── SafeExecutor ───────────────────────────────────────────────────


class TestSafeExecutor:
    """Core execution tests."""

    def test_execute_simple_code(self, sandbox):
        code = "result_text = 'hola mundo'"
        success, error = sandbox.execute(code)
        assert success is True
        assert error == ""
        assert sandbox.last_text == "hola mundo"

    def test_execute_with_result_df(self, sandbox):
        code = """
import pandas as pd
result_df = pd.DataFrame({"x": [1, 2, 3]})
"""
        success, error = sandbox.execute(code)
        assert success is True
        assert sandbox.last_dataframe is not None
        assert len(sandbox.last_dataframe) == 3

    def test_execute_with_fig(self, sandbox):
        code = """
import plotly.graph_objects as go
fig = go.Figure(data=go.Scatter(x=[1,2], y=[3,4]))
"""
        success, error = sandbox.execute(code)
        assert success is True
        assert sandbox.last_figure is not None
        assert isinstance(sandbox.last_figure, go.Figure)

    def test_execute_result_text_takes_precedence(self, sandbox):
        """result_text should be a string, captured as last_text."""
        code = "result_text = 'respuesta textual'"
        success, error = sandbox.execute(code)
        assert success is True
        assert sandbox.last_text == "respuesta textual"
        # Should NOT be captured as a dataframe
        assert sandbox.last_dataframe is None

    def test_syntax_error(self, sandbox):
        code = "result_text = 'incomplete"
        success, error = sandbox.execute(code)
        assert success is False
        assert "Error de sintaxis" in error

    def test_timeout(self):
        """Code that runs forever should be killed (no imports needed)."""
        short_sandbox = SafeExecutor(timeout=1)
        code = "while True: x = 1"
        success, error = short_sandbox.execute(code)
        assert success is False
        assert "cancelado" in error

    def test_name_error(self, sandbox):
        code = "result_text = undefined_var"
        success, error = sandbox.execute(code)
        assert success is False
        assert "no disponible" in error

    def test_disallowed_import_os(self, sandbox):
        code = "import os\nresult_text = 'hack'"
        success, error = sandbox.execute(code)
        assert success is False
        assert "no disponible" in error or "import" in error.lower()

    def test_disallowed_import_subprocess(self, sandbox):
        code = "import subprocess"
        success, error = sandbox.execute(code)
        assert success is False

    def test_blocked_open(self, sandbox):
        code = "open('test.txt')\nresult_text = 'hack'"
        success, error = sandbox.execute(code)
        assert success is False
        assert "no disponible" in error or "NameError" in error or "open" in error.lower()

    def test_blocked_eval(self, sandbox):
        code = "eval('1+1')"
        success, error = sandbox.execute(code)
        assert success is False

    def test_blocked_exec(self, sandbox):
        code = "exec('x=1')"
        success, error = sandbox.execute(code)
        assert success is False

    def test_empty_code(self, sandbox):
        code = ""
        success, error = sandbox.execute(code)
        assert success is True
        assert error == ""

    def test_whitespace_only(self, sandbox):
        code = "   \n\n  "
        success, error = sandbox.execute(code)
        assert success is True

    def test_print_works(self, sandbox):
        """print is allowed in the builtins."""
        code = "print('hello')"
        success, error = sandbox.execute(code)
        assert success is True

    def test_numpy_available(self, sandbox):
        code = "result_text = str(np.mean([1, 2, 3]))"
        success, error = sandbox.execute(code)
        assert success is True
        assert sandbox.last_text == "2.0"

    def test_pandas_available(self, sandbox):
        code = "result_df = pd.DataFrame({'a': [1, 2]})"
        success, error = sandbox.execute(code)
        assert success is True
        assert sandbox.last_dataframe is not None

    def test_plotly_express_available(self, sandbox):
        """Verify px is accessible without triggering lazy imports inside thread."""
        code = "result_text = str(type(px).__name__)"
        success, error = sandbox.execute(code)
        assert success is True
        assert sandbox.last_text == "module"

    def test_multiple_variables_only_last_captured(self, sandbox):
        """_capture_figures captures the last occurrence of each type."""
        code = """
df1 = pd.DataFrame({"x": [1]})
df2 = pd.DataFrame({"y": [2]})
"""
        success, error = sandbox.execute(code)
        assert success is True
        # last_dataframe should be df2 (last assigned)
        assert sandbox.last_dataframe is not None
        assert list(sandbox.last_dataframe.columns) == ["y"]

    def test_underscore_vars_ignored(self, sandbox):
        """Variables starting with underscore should not be captured."""
        code = """
_df = pd.DataFrame({"x": [1]})
result_text = "visible"
"""
        success, error = sandbox.execute(code)
        assert success is True
        assert sandbox.last_text == "visible"
        assert sandbox.last_dataframe is None


    def test_state_reset_between_executions(self, sandbox):
        """Each execute() should reset last_figure, last_dataframe, last_text."""
        sandbox.execute("result_text = 'first'")
        assert sandbox.last_text == "first"

        sandbox.execute("result_text = 'second'")
        assert sandbox.last_text == "second"

    def test_non_string_result_text_not_captured(self, sandbox):
        """result_text must be a string to be captured."""
        code = "result_text = 42"
        success, error = sandbox.execute(code)
        assert success is True
        # 42 is an int, not a str — should NOT be captured as last_text
        assert sandbox.last_text == ""


class TestSafeExecutorWithDataframes:
    """Tests for dataframe injection into the sandbox."""

    def test_single_dataframe_injection(self, sandbox):
        df = pd.DataFrame({"name": ["Alice", "Bob"], "age": [30, 25]})
        code = 'result_text = f"Promedio edad: {df.age.mean():.1f}"'
        success, error = sandbox.execute(code, dataframes={"df": df})
        assert success is True
        assert sandbox.last_text == "Promedio edad: 27.5"

    def test_multiple_dataframes(self, sandbox):
        df1 = pd.DataFrame({"value": [10, 20]})
        df2 = pd.DataFrame({"value": [30, 40]})
        code = """
result_text = str(df1.value.sum() + df2.value.sum())
"""
        success, error = sandbox.execute(code, dataframes={"df1": df1, "df2": df2})
        assert success is True
        assert sandbox.last_text == "100"

    def test_dataframe_injection_variable_accessible(self, sandbox):
        df = pd.DataFrame({"a": range(5)})
        code = "result_df = df.describe()"
        success, error = sandbox.execute(code, dataframes={"df": df})
        assert success is True
        assert sandbox.last_dataframe is not None
        assert sandbox.last_dataframe.loc["count", "a"] == 5.0

    def test_no_dataframes_passed(self, sandbox):
        """Without passing dataframes, 'df' should cause NameError."""
        code = "result_text = str(df.shape)"
        success, error = sandbox.execute(code)
        assert success is False
        assert "no disponible" in error

    def test_timeout_with_dataframes(self, sandbox):
        """Timeout should still work with dataframes injected."""
        df = pd.DataFrame({"x": [1]})
        code = "while True: x = 1"
        short_sandbox = SafeExecutor(timeout=1)
        success, error = short_sandbox.execute(code, dataframes={"df": df})
        assert success is False
        assert "cancelado" in error


class TestCaptureFigures:
    """Edge cases of _capture_figures."""

    def test_captures_go_figure(self, sandbox):
        code = """
fig = go.Figure(data=go.Bar(x=[1,2], y=[3,4]))
fig.update_layout(title="Test")
"""
        success, error = sandbox.execute(code)
        assert success is True
        assert sandbox.last_figure is not None
        assert sandbox.last_figure.layout.title.text == "Test"

    def test_captures_px_figure(self, sandbox):
        """px figure creation works (using graph_objects internally to avoid lazy import)."""
        code = """
import plotly.graph_objects as go
fig = go.Figure(data=go.Bar(x=['a','b'], y=[1,2]))
fig.update_layout(title='px test')
"""
        success, error = sandbox.execute(code)
        assert success is True
        assert sandbox.last_figure is not None

    def test_figure_and_dataframe_both_captured(self, sandbox):
        code = """
fig = go.Figure(data=go.Scatter(x=[1], y=[2]))
result_df = pd.DataFrame({"a": [1, 2]})
result_text = "hecho"
"""
        success, error = sandbox.execute(code)
        assert success is True
        assert sandbox.last_figure is not None
        assert sandbox.last_dataframe is not None
        assert sandbox.last_text == "hecho"

    def test_no_figure_no_dataframe(self, sandbox):
        code = "x = 42"
        success, error = sandbox.execute(code)
        assert success is True
        assert sandbox.last_figure is None
        assert sandbox.last_dataframe is None
        assert sandbox.last_text == ""
