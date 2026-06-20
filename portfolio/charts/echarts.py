"""Apache ECharts renderer and dashboard chart builders."""

from __future__ import annotations

import json
import uuid
from typing import Any

import streamlit as st

from portfolio.errors import ChartRenderError
from portfolio.logger import get_logger

logger = get_logger(__name__)


def _render_echarts_option(option: dict[str, Any], height: int = 400) -> None:
    chart_id = f"chart_{uuid.uuid4().hex[:10]}"
    option_json = json.dumps(option, default=str)
    html = f"""
<div id="{chart_id}" style="width:100%;height:{height}px;"></div>
<script type="text/javascript">
(function () {{
  function initChart() {{
    var el = document.getElementById("{chart_id}");
    if (!el || typeof echarts === "undefined") return;
    var chart = echarts.init(el);
    chart.setOption({option_json});
    window.addEventListener("resize", function () {{ chart.resize(); }});
  }}
  if (typeof echarts !== "undefined") {{
    initChart();
  }} else {{
    var s = document.createElement("script");
    s.src = "https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js";
    s.onload = initChart;
    document.head.appendChild(s);
  }}
}})();
</script>
"""
    try:
        st.html(html, unsafe_allow_javascript=True)
    except Exception as exc:
        logger.exception("ECharts render failed")
        raise ChartRenderError(str(exc)) from exc


def render_line_chart(
    title: str,
    x_data: list,
    series: list[dict[str, Any]],
    y_axis_name: str = "",
    height: int = 360,
) -> None:
    _render_echarts_option(
        {
            "title": {"text": title, "left": "center", "textStyle": {"fontSize": 14}},
            "tooltip": {"trigger": "axis"},
            "legend": {"top": 28},
            "grid": {"left": 56, "right": 24, "top": 72, "bottom": 48},
            "xAxis": {"type": "category", "data": x_data, "boundaryGap": False},
            "yAxis": {"type": "value", "name": y_axis_name},
            "series": series,
        },
        height=height,
    )


def render_allocation_bar_chart(title: str, categories: list[str], weights_pct: list[float], height: int = 320) -> None:
    _render_echarts_option(
        {
            "title": {"text": title, "left": "center"},
            "tooltip": {"trigger": "axis"},
            "grid": {"left": 56, "right": 24, "top": 64, "bottom": 48},
            "xAxis": {"type": "category", "data": categories},
            "yAxis": {"type": "value", "name": "Weight"},
            "series": [
                {
                    "type": "bar",
                    "data": [float(value) for value in weights_pct],
                    "itemStyle": {"color": "#5470c6"},
                    "label": {"show": True, "formatter": "{c}%", "position": "top"},
                }
            ],
        },
        height=height,
    )


def render_correlation_heatmap(title: str, labels: list[str], matrix: list[list[float]], height: int = 360) -> None:
    data = [[j, i, round(float(value), 3)] for i, row in enumerate(matrix) for j, value in enumerate(row)]
    _render_echarts_option(
        {
            "title": {"text": title, "left": "center"},
            "tooltip": {"position": "top"},
            "grid": {"height": "62%", "top": "14%", "left": 80, "right": 40},
            "xAxis": {"type": "category", "data": labels, "splitArea": {"show": True}},
            "yAxis": {"type": "category", "data": labels, "splitArea": {"show": True}},
            "visualMap": {
                "min": -1,
                "max": 1,
                "calculable": True,
                "orient": "horizontal",
                "left": "center",
                "bottom": "2%",
            },
            "series": [{"name": "Correlation", "type": "heatmap", "data": data, "label": {"show": True}}],
        },
        height=height,
    )


def render_distribution_chart(
    title: str,
    bin_centers: list[float],
    counts: list[int],
    normal_x: list[float],
    normal_y: list[float],
    height: int = 360,
) -> None:
    if not bin_centers or not counts:
        return

    categories = [f"{center:.2f}" for center in bin_centers]
    normal_map = {f"{x:.2f}": float(y) for x, y in zip(normal_x, normal_y)}
    _render_echarts_option(
        {
            "title": {"text": title, "left": "center"},
            "tooltip": {"trigger": "axis"},
            "legend": {"top": 28, "data": ["Observed count", "Normal density"]},
            "grid": {"left": 56, "right": 24, "top": 72, "bottom": 48},
            "xAxis": {
                "type": "category",
                "data": categories,
                "name": "Daily return (%)",
                "axisLabel": {"rotate": 45, "interval": 2},
            },
            "yAxis": [
                {"type": "value", "name": "Count"},
                {"type": "value", "name": "Density", "splitLine": {"show": False}},
            ],
            "series": [
                {
                    "name": "Observed count",
                    "type": "bar",
                    "data": [int(count) for count in counts],
                    "itemStyle": {"opacity": 0.7, "color": "#91cc75"},
                },
                {
                    "name": "Normal density",
                    "type": "line",
                    "yAxisIndex": 1,
                    "smooth": True,
                    "showSymbol": False,
                    "data": [normal_map.get(category, 0.0) for category in categories],
                    "lineStyle": {"width": 2, "color": "#ee6666"},
                },
            ],
        },
        height=height,
    )


def render_gaussian_risk_chart(
    title: str,
    x_pct: list[float],
    density: list[float],
    loss_threshold: float = 0.0,
    height: int = 360,
) -> None:
    curve = [[float(x), float(y)] for x, y in zip(x_pct, density)]
    _render_echarts_option(
        {
            "title": {"text": title, "left": "center"},
            "tooltip": {"trigger": "axis"},
            "grid": {"left": 56, "right": 24, "top": 64, "bottom": 56},
            "xAxis": {"type": "value", "name": "Monthly return (%)", "nameLocation": "middle", "nameGap": 32},
            "yAxis": {"type": "value", "name": "Probability density"},
            "series": [
                {
                    "type": "line",
                    "smooth": True,
                    "showSymbol": False,
                    "areaStyle": {"opacity": 0.25, "color": "#5470c6"},
                    "data": curve,
                    "markLine": {
                        "data": [{"xAxis": loss_threshold, "label": {"formatter": "Break-even"}}],
                        "lineStyle": {"color": "#999", "type": "dashed"},
                    },
                }
            ],
        },
        height=height,
    )


def render_efficient_frontier_chart(
    title: str,
    frontier_vol: list[float],
    frontier_ret: list[float],
    assets: list[dict[str, float]],
    optimal: dict[str, float],
    height: int = 400,
) -> None:
    _render_echarts_option(
        {
            "title": {"text": title, "left": "center"},
            "tooltip": {"trigger": "item"},
            "grid": {"left": 64, "right": 24, "top": 72, "bottom": 56},
            "xAxis": {"type": "value", "name": "Volatility (annual %)"},
            "yAxis": {"type": "value", "name": "Expected return (annual %)"},
            "series": [
                {
                    "name": "Efficient frontier",
                    "type": "line",
                    "smooth": True,
                    "showSymbol": False,
                    "data": [[float(v), float(r)] for v, r in zip(frontier_vol, frontier_ret)],
                    "lineStyle": {"color": "#5470c6"},
                },
                {
                    "name": "Assets",
                    "type": "scatter",
                    "symbolSize": 14,
                    "data": [[a["vol"] * 100, a["return"] * 100, a["name"]] for a in assets],
                },
                {
                    "name": "Optimal portfolio",
                    "type": "scatter",
                    "symbolSize": 18,
                    "itemStyle": {"color": "#ee6666"},
                    "data": [[optimal["vol"] * 100, optimal["return"] * 100]],
                },
            ],
        },
        height=height,
    )


def render_capm_line_chart(
    risk_free_rate_annual: float,
    capm_expected_return: float,
    stock_beta: float,
    stock_annual_return: float,
    height: int = 360,
) -> None:
    _render_echarts_option(
        {
            "title": {
                "text": "Capital Market Line (CAPM)",
                "left": "center",
                "textStyle": {"fontSize": 14},
            },
            "tooltip": {"trigger": "axis"},
            "legend": {"top": 28},
            "grid": {"left": 64, "right": 24, "top": 72, "bottom": 48},
            "xAxis": {"type": "value", "name": "Beta"},
            "yAxis": {"type": "value", "name": "Expected return (annual %)"},
            "series": [
                {
                    "name": "CAPM line",
                    "type": "line",
                    "data": [
                        [0, risk_free_rate_annual * 100],
                        [1, capm_expected_return * 100],
                        [max(stock_beta, 0.1), capm_expected_return * 100],
                    ],
                    "lineStyle": {"color": "#91cc75"},
                },
                {
                    "name": "Stock",
                    "type": "scatter",
                    "symbolSize": 16,
                    "data": [[stock_beta, stock_annual_return * 100]],
                },
            ],
        },
        height=height,
    )
