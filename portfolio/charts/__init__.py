"""Apache ECharts rendering for the dashboard."""

from portfolio.charts.echarts import (
    render_allocation_bar_chart,
    render_capm_line_chart,
    render_correlation_heatmap,
    render_distribution_chart,
    render_efficient_frontier_chart,
    render_gaussian_risk_chart,
    render_line_chart,
)

__all__ = [
    "render_line_chart",
    "render_allocation_bar_chart",
    "render_correlation_heatmap",
    "render_distribution_chart",
    "render_gaussian_risk_chart",
    "render_efficient_frontier_chart",
    "render_capm_line_chart",
]
