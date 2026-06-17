"""Tests for services/code_executor.py — _sanitize_varname, _build_dataframe_map."""

import pandas as pd

from models.file_data import FileData
from services.code_executor import _sanitize_varname, CodeExecutor


# ── _sanitize_varname ──────────────────────────────────────────────


class TestSanitizeVarname:
    def test_basic_filename(self):
        assert _sanitize_varname("Computers.csv") == "df_Computers"

    def test_filename_with_spaces(self):
        assert _sanitize_varname("my data.csv") == "df_my_data"

    def test_filename_with_hyphens(self):
        assert _sanitize_varname("my-data.csv") == "df_my_data"

    def test_filename_with_parens(self):
        assert _sanitize_varname("datos (1).xlsx") == "df_datos_1"

    def test_multiple_special_chars(self):
        assert _sanitize_varname("sales!@#report.csv") == "df_sales_report"

    def test_multiple_underscores_collapsed(self):
        assert _sanitize_varname("a__b___c.csv") == "df_a_b_c"

    def test_leading_trailing_underscores_stripped(self):
        assert _sanitize_varname("_data_.csv") == "df_data"

    def test_empty_stem(self):
        # Path(".csv").stem returns ".csv" → regex keeps "csv"
        assert _sanitize_varname(".csv") == "df_csv"

    def test_excel_file(self):
        assert _sanitize_varname("Reporte Ventas.xlsx") == "df_Reporte_Ventas"

    def test_numeric_filename(self):
        assert _sanitize_varname("123data.csv") == "df_123data"

    def test_pure_numeric_stem(self):
        assert _sanitize_varname("123.csv") == "df_123"

    def test_filename_with_dots(self):
        assert _sanitize_varname("data.clean.final.csv") == "df_data_clean_final"

    def test_uppercase_filename(self):
        result = _sanitize_varname("COMPUTERS.csv")
        # Should handle uppercase — the _sanitize_varname doesn't lowercase explicitly
        # but the regex only keeps alphanumeric, so "COMPUTERS" stays uppercase
        assert result == "df_COMPUTERS"


# ── _build_dataframe_map ───────────────────────────────────────────


class TestBuildDataframeMap:
    def test_single_file(self):
        files = [FileData(filename="computers.csv", df=pd.DataFrame({"a": [1]}))]
        df_map, names = CodeExecutor._build_dataframe_map(files)

        assert "df" in df_map
        assert "df_computers" in df_map
        assert df_map["df"] is files[0].df
        assert df_map["df_computers"] is files[0].df
        assert names == ["df_computers"]

    def test_two_files(self):
        df1 = pd.DataFrame({"x": [1]})
        df2 = pd.DataFrame({"y": [2]})
        files = [
            FileData(filename="first.csv", df=df1),
            FileData(filename="second.csv", df=df2),
        ]
        df_map, names = CodeExecutor._build_dataframe_map(files)

        assert "df_first_1" in df_map
        assert "df_second_2" in df_map
        # First file is also exposed as `df`
        assert "df" in df_map
        assert df_map["df"] is df1
        assert names == ["df_first_1", "df_second_2"]

    def test_three_files(self):
        files = [
            FileData(filename="a.csv", df=pd.DataFrame({"a": [1]})),
            FileData(filename="b.csv", df=pd.DataFrame({"b": [2]})),
            FileData(filename="c.csv", df=pd.DataFrame({"c": [3]})),
        ]
        df_map, names = CodeExecutor._build_dataframe_map(files)
        assert len(names) == 3
        assert names == ["df_a_1", "df_b_2", "df_c_3"]
        assert "df" in df_map

    def test_empty_files_list(self):
        df_map, names = CodeExecutor._build_dataframe_map([])
        assert df_map == {}
        assert names == []

    def test_file_with_same_stem(self):
        """Files with same stem in different dirs or renamed — still works."""
        files = [
            FileData(filename="data.csv", df=pd.DataFrame({"a": [1]})),
            FileData(filename="data_2.csv", df=pd.DataFrame({"b": [2]})),
        ]
        df_map, names = CodeExecutor._build_dataframe_map(files)
        # _sanitize_varname on both would give df_data and df_data_2
        assert len(names) == 2


# ── CodeExecutor initialization ────────────────────────────────────


class TestCodeExecutorInit:
    def test_default_sandbox_created(self):
        executor = CodeExecutor(llm_service=None)  # type: ignore
        assert executor.sandbox is not None
        from utils.sandbox import SafeExecutor
        assert isinstance(executor.sandbox, SafeExecutor)

    def test_custom_sandbox_injected(self):
        from utils.sandbox import SafeExecutor
        custom = SafeExecutor(timeout=5)
        executor = CodeExecutor(llm_service=None, sandbox=custom)  # type: ignore
        assert executor.sandbox is custom
        assert executor.sandbox.timeout == 5
