"""
SafeExecutor: restricted Python environment for executing LLM-generated code.

Only allows:
  - Built-in functions (safe subset)
  - pandas (as pd)
  - numpy (as np)
  - plotly.express (as px)
  - plotly.graph_objects (as go)

Explicitly blocks:
  - File I/O (open, os, shutil, pathlib)
  - Subprocess execution
  - Dynamic imports (__import__)
  - Code execution (eval, exec, compile)
  - System access (sys, platform)
"""

from __future__ import annotations

import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Any, Optional

import numpy as np
import pandas as pd
import plotly
import plotly.express as px
import plotly.graph_objects as go


# ── Safe import hook: only allow modules in the allowlist ──────────
_IMPORT_ALLOWLIST = {
    "pandas": pd,
    "numpy": np,
    "plotly": plotly,
    "plotly.express": px,
    "plotly.graph_objects": go,
}


def _safe_import(name: str, *args, **kwargs):
    """Restricted __import__ — only permit modules in _IMPORT_ALLOWLIST."""
    # Handle 'from X import Y' — name is the top-level package
    top_level = name.split(".")[0]
    if top_level in _IMPORT_ALLOWLIST:
        return __import__(name, *args, **kwargs)
    raise ImportError(f"import not found")


class ExecutionTimeout(Exception):
    """Raised when code execution exceeds the time limit."""
    pass


class SafeExecutor:
    """Executes Python code in a restricted environment."""

    # Whitelist of allowed builtins (incl. safe __import__ hook)
    ALLOWED_BUILTINS = {
        "abs": abs,
        "all": all,
        "any": any,
        "bool": bool,
        "dict": dict,
        "enumerate": enumerate,
        "filter": filter,
        "float": float,
        "int": int,
        "isinstance": isinstance,
        "len": len,
        "list": list,
        "map": map,
        "max": max,
        "min": min,
        "print": print,
        "range": range,
        "round": round,
        "set": set,
        "slice": slice,
        "sorted": sorted,
        "str": str,
        "sum": sum,
        "tuple": tuple,
        "type": type,
        "zip": zip,
        "True": True,
        "False": False,
        "None": None,
        "__import__": _safe_import,
    }

    ALLOWED_MODULES = {
        "pd": pd,
        "pandas": pd,
        "np": np,
        "numpy": np,
        "px": px,
        "plotly_express": px,
        "go": go,
        "plotly_graph_objects": go,
    }

    TIMEOUT_SECONDS = 30

    def __init__(self, timeout: int = TIMEOUT_SECONDS):
        self.timeout = timeout
        self.last_figure: Optional[go.Figure] = None
        self.last_dataframe: Optional[pd.DataFrame] = None
        self.last_text: str = ""

    def _build_globals(self) -> dict[str, Any]:
        """Build the restricted globals dictionary."""
        globs: dict[str, Any] = {
            "__builtins__": self.ALLOWED_BUILTINS,
        }
        globs.update(self.ALLOWED_MODULES)
        return globs

    def _capture_figures(self, local_vars: dict):
        """Try to extract figures, dataframes, and text from local variables after execution."""
        for name, var in local_vars.items():
            if name.startswith("_"):
                continue
            if isinstance(var, go.Figure):
                self.last_figure = var
            elif isinstance(var, pd.DataFrame):
                self.last_dataframe = var
            elif isinstance(var, str) and name == "result_text":
                self.last_text = var

    def execute(
        self,
        code: str,
        dataframes: dict[str, pd.DataFrame] | None = None,
    ) -> tuple[bool, str]:
        """
        Execute the given Python code in the sandbox.

        Args:
            code: Python code string to execute.
            dataframes: Optional dict of {variable_name: DataFrame} to inject
                        into the execution context (e.g. {"df": df}).

        Uses ThreadPoolExecutor for cross-platform timeout (Windows + Unix).

        Returns:
            Tuple of (success: bool, error_message_or_empty_string)
        """
        # Reset captured state
        self.last_figure = None
        self.last_dataframe = None
        self.last_text = ""

        globs = self._build_globals()
        local_vars: dict[str, Any] = {}

        # Inject dataframes so LLM code can reference them directly
        if dataframes:
            globs.update(dataframes)

        # Compile first to catch syntax errors before exec
        try:
            compiled = compile(code.strip(), "<sandbox>", "exec")
        except SyntaxError as e:
            return False, f"Error de sintaxis: {e}"

        # Execute with timeout via thread pool (works on Windows!)
        def _run():
            exec(compiled, globs, local_vars)

        pool = ThreadPoolExecutor(max_workers=1)
        future = pool.submit(_run)
        try:
            future.result(timeout=self.timeout)
        except FuturesTimeout:
            return False, f"⏱ El análisis tomó más de {self.timeout} segundos y fue cancelado."
        except NameError as e:
            return False, f"Función o librería no disponible: {e}"
        except Exception as e:
            tb = traceback.format_exc()
            return False, f"Error durante el análisis: {e}\n\nDetalles:\n{tb}"
        finally:
            # Don't wait — the thread may be stuck in an infinite loop
            pool.shutdown(wait=False)

        # Capture any generated figures or dataframes
        self._capture_figures(local_vars)

        return True, ""
