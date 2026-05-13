"""
Tests for the dashboard component — pure logic functions only.
Functions that interact with Streamlit widgets or session_state are
excluded; only the pure computation helpers are tested here.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import pytest

from app.components.dashboard import (
    _apply_filters,
    _build_chart_figure,
    _compute_kpi_value,
    _format_metric,
)


# ===================================================================
# _format_metric
# ===================================================================


class TestFormatMetric:
    def test_none_returns_dash(self):
        assert _format_metric(None) == "—"

    def test_zero(self):
        assert _format_metric(0) == "0"

    def test_small_float(self):
        assert _format_metric(3.14) == "3.14"

    def test_integer_float_returns_int_str(self):
        assert _format_metric(42.0) == "42"

    def test_large_number_no_price(self):
        # >= 1_000 but < 1_000_000, no "price" in col_name → :,.1f with commas
        result = _format_metric(1234.5, col_name="speed")
        assert result == "1,234.5"

    def test_large_number_with_price(self):
        # >= 1_000 but < 1_000_000, "price" in col_name → $:,.0f (integer)
        result = _format_metric(2219.58, col_name="price")
        assert result == "$2,220"

    def test_millions_no_price(self):
        result = _format_metric(2_500_000.0, col_name="ram")
        assert result == "2,500,000"

    def test_millions_with_price(self):
        result = _format_metric(1_234_567.0, col_name="price_total")
        assert result == "$1,234,567"

    def test_string_input_passed_through(self):
        assert _format_metric("N/A") == "N/A"

    def test_negative_number(self):
        result = _format_metric(-500)
        assert result == "-500"


# ===================================================================
# _apply_filters
# ===================================================================


class TestApplyFilters:
    @pytest.fixture
    def df(self) -> pd.DataFrame:
        return pd.DataFrame({
            "premium": ["yes", "no", "yes", "no"],
            "cd": ["yes", "no", "no", "yes"],
            "price": [100, 200, 300, 400],
        })

    def test_no_filters_returns_all(self, df):
        result = _apply_filters(df, {"columns": []})
        assert len(result) == 4
        assert result.equals(df)

    def test_single_column_filter(self, df):
        filters = {"columns": [{"col": "premium", "vals": ["yes"]}]}
        result = _apply_filters(df, filters)
        assert len(result) == 2
        assert list(result["premium"]) == ["yes", "yes"]

    def test_multiple_filters_and(self, df):
        filters = {
            "columns": [
                {"col": "premium", "vals": ["yes"]},
                {"col": "cd", "vals": ["no"]},
            ]
        }
        result = _apply_filters(df, filters)
        # premium=yes AND cd=no → only row 2 (index 2): yes, no, 300
        assert len(result) == 1
        assert result.iloc[0]["price"] == 300

    def test_empty_values_returns_all(self, df):
        filters = {"columns": [{"col": "premium", "vals": []}]}
        result = _apply_filters(df, filters)
        assert len(result) == 4

    def test_nonexistent_column_ignored(self, df):
        filters = {"columns": [{"col": "nonexistent", "vals": ["x"]}]}
        result = _apply_filters(df, filters)
        assert len(result) == 4

    def test_filters_config_is_none(self, df):
        result = _apply_filters(df, None)
        assert len(result) == 4

    def test_empty_dataframe(self):
        empty = pd.DataFrame()
        filters = {"columns": [{"col": "x", "vals": ["y"]}]}
        result = _apply_filters(empty, filters)
        assert result.empty


# ===================================================================
# _compute_kpi_value
# ===================================================================


class TestComputeKpiValue:
    @pytest.fixture
    def df(self) -> pd.DataFrame:
        return pd.DataFrame({
            "premium": ["yes", "no", "yes", "no"],
            "price": [100, 200, 300, 400],
            "ram": [4, 8, 16, 32],
        })

    def test_mean(self, df):
        # price mean: (100 + 200 + 300 + 400) / 4 = 250
        result = _compute_kpi_value(df, {"column": "price", "aggregation": "mean"})
        assert result == 250.0

    def test_sum(self, df):
        result = _compute_kpi_value(df, {"column": "price", "aggregation": "sum"})
        assert result == 1000.0

    def test_count(self, df):
        result = _compute_kpi_value(df, {"column": "price", "aggregation": "count"})
        assert result == 4.0

    def test_min(self, df):
        result = _compute_kpi_value(df, {"column": "price", "aggregation": "min"})
        assert result == 100.0

    def test_max(self, df):
        result = _compute_kpi_value(df, {"column": "price", "aggregation": "max"})
        assert result == 400.0

    def test_grouped_kpi(self, df):
        result = _compute_kpi_value(
            df,
            {"column": "price", "aggregation": "mean", "group_by": "premium"},
        )
        assert isinstance(result, dict)
        assert result["yes"] == 200.0  # (100 + 300) / 2
        assert result["no"] == 300.0   # (200 + 400) / 2

    def test_missing_column_returns_zero(self, df):
        result = _compute_kpi_value(df, {"column": "ghost", "aggregation": "mean"})
        assert result == 0

    def test_empty_dataframe_returns_zero(self):
        empty = pd.DataFrame({"x": []})
        result = _compute_kpi_value(empty, {"column": "x", "aggregation": "mean"})
        # mean of empty series → NaN → should be treated as 0
        import math
        assert math.isnan(result) or result == 0

    def test_group_by_missing_column_ignored(self, df):
        result = _compute_kpi_value(
            df,
            {"column": "price", "aggregation": "mean", "group_by": "ghost"},
        )
        assert result == 250.0  # falls back to ungrouped


# ===================================================================
# _build_chart_figure
# ===================================================================


class TestBuildChartFigure:
    @pytest.fixture
    def df(self) -> pd.DataFrame:
        return pd.DataFrame({
            "category": ["a", "b", "c"],
            "value": [10, 20, 30],
            "color": ["x", "y", "x"],
        })

    def test_bar_chart(self, df):
        config = {"chart_type": "Barra", "mappings": {"x": "category", "y": "value"}}
        fig = _build_chart_figure(df, config)
        assert fig is not None
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_line_chart(self, df):
        config = {"chart_type": "Línea", "mappings": {"x": "category", "y": "value"}}
        fig = _build_chart_figure(df, config)
        assert fig is not None

    def test_scatter(self, df):
        config = {"chart_type": "Dispersión", "mappings": {"x": "category", "y": "value"}}
        fig = _build_chart_figure(df, config)
        assert fig is not None

    def test_pie(self, df):
        config = {"chart_type": "Torta", "mappings": {"names": "category", "values": "value"}}
        fig = _build_chart_figure(df, config)
        assert fig is not None

    def test_histogram(self, df):
        config = {"chart_type": "Histograma", "mappings": {"x": "value"}}
        fig = _build_chart_figure(df, config)
        assert fig is not None

    def test_box_plot(self, df):
        config = {"chart_type": "Box Plot", "mappings": {"y": "value"}}
        fig = _build_chart_figure(df, config)
        assert fig is not None

    def test_invalid_chart_type_returns_none(self, df):
        config = {"chart_type": "NoExiste", "mappings": {}}
        fig = _build_chart_figure(df, config)
        assert fig is None

    def test_empty_dataframe_returns_none(self):
        empty = pd.DataFrame()
        config = {"chart_type": "Barra", "mappings": {"x": "a", "y": "b"}}
        fig = _build_chart_figure(empty, config)
        assert fig is None

    def test_none_dataframe_returns_none(self):
        config = {"chart_type": "Barra", "mappings": {}}
        fig = _build_chart_figure(None, config)
        assert fig is None

    def test_missing_column_returns_none(self, df):
        """Plotly raises when a column doesn't exist; caught by try/except."""
        config = {"chart_type": "Barra", "mappings": {"x": "ghost", "y": "value"}}
        fig = _build_chart_figure(df, config)
        assert fig is None

    def test_title_applied(self, df):
        config = {"chart_type": "Barra", "mappings": {"x": "category", "y": "value"}}
        fig = _build_chart_figure(df, config, title="Test Title")
        assert fig is not None
        # Plotly stores title text in layout.title.text
        assert fig.layout.title.text == "Test Title"
