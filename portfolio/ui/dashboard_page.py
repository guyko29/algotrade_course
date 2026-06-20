"""Portfolio dashboard page."""

from __future__ import annotations

from contextlib import contextmanager
from math import expm1
from typing import Iterator

import streamlit as st

from portfolio.analytics.models import PortfolioAnalysis
from portfolio.analytics.portfolio_service import PortfolioAnalysisService
from portfolio.analytics.prices import compute_log_returns
from portfolio.analytics.risk_metrics import classify_risk_level
from portfolio.config import get_settings
from portfolio.charts.echarts import (
    render_allocation_bar_chart,
    render_capm_line_chart,
    render_correlation_heatmap,
    render_distribution_chart,
    render_efficient_frontier_chart,
    render_feature_importance_chart,
    render_gaussian_risk_chart,
    render_line_chart,
)
from portfolio.constants import PORTFOLIO_ASSET_LABELS, TA125_INDEX_ID, TRADING_DAYS_PER_YEAR
from portfolio.errors import ChartRenderError, PortfolioError, display_error
from portfolio.ui.session import should_reload_analysis


def _inject_dashboard_styles() -> None:
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"] {
            padding: 1.25rem 1.5rem 1.5rem;
            margin-bottom: 1.25rem;
            border-radius: 10px;
            background-color: rgba(240, 242, 246, 0.35);
        }
        div[data-testid="stVerticalBlockBorderWrapper"] h3 {
            margin-top: 0;
            padding-bottom: 0.25rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@contextmanager
def _dashboard_section(title: str) -> Iterator[None]:
    with st.container(border=True):
        st.subheader(title)
        yield


def _load_analysis(
    stock_id: int,
    benchmark_id: int,
    risk_free_rate_annual: float,
) -> PortfolioAnalysis | None:
    st.title("Building your dashboard...")
    st.warning(
        "Downloading market data from the Tel Aviv Stock Exchange. "
        "**This usually takes 30–60 seconds.** Please keep this tab open."
    )
    progress_bar = st.progress(0.0, text="Starting...")
    status_box = None

    def on_progress(fraction: float, message: str) -> None:
        progress_bar.progress(min(max(fraction, 0.0), 1.0), text=message)

    try:
        with st.status("Loading in progress", expanded=True) as status_box:
            service = PortfolioAnalysisService()
            analysis = service.build_analysis(
                stock_id=stock_id,
                benchmark_id=benchmark_id,
                risk_free_rate_annual=risk_free_rate_annual,
                on_progress=on_progress,
            )
            status_box.update(label="Data loaded successfully", state="complete")
        return analysis
    except PortfolioError as exc:
        if status_box is not None:
            status_box.update(label="Could not complete analysis", state="error")
        display_error(st, exc)
        return None
    except Exception as exc:
        if status_box is not None:
            status_box.update(label="Unexpected error", state="error")
        display_error(st, exc)
        return None


def _annualize_log_daily(daily_log_return: float) -> float:
    """Daily log return -> annualized simple return, for display."""
    return expm1(daily_log_return * TRADING_DAYS_PER_YEAR)


def _safe_chart(render_fn, *args, **kwargs) -> None:
    try:
        render_fn(*args, **kwargs)
    except ChartRenderError as exc:
        display_error(st, exc)


def render_dashboard_page(stock_id: int, benchmark_id: int, risk_free_rate_annual: float) -> None:
    if should_reload_analysis(stock_id, benchmark_id, risk_free_rate_annual) or st.session_state.loading:
        analysis = _load_analysis(stock_id, benchmark_id, risk_free_rate_annual)
        st.session_state.loading = False
        st.session_state.force_reload = False
        if analysis is None:
            st.stop()
        st.session_state.analysis = analysis
        st.session_state.loaded_stock_id = stock_id
        st.session_state.stock_id = stock_id
        st.session_state.benchmark_id = benchmark_id
        st.session_state.risk_free_rate_annual = risk_free_rate_annual
        st.rerun()

    _inject_dashboard_styles()

    analysis: PortfolioAnalysis = st.session_state.analysis
    metrics = analysis.metrics
    capm = analysis.capm
    portfolio = analysis.portfolio
    benchmark_name = "TA-125" if analysis.benchmark_id == TA125_INDEX_ID else "TA-35"

    if analysis.benchmark_requested == TA125_INDEX_ID and analysis.benchmark_id != TA125_INDEX_ID:
        st.info("TA-125 is unavailable on the public API. Results use TA-35 as the market benchmark.")

    stock_title = st.session_state.get("stock_label") or f"Security {analysis.stock_id}"
    st.title(f"Portfolio Dashboard — {stock_title}")
    st.caption(
        f"Benchmark: {benchmark_name} · Risk-free rate: {analysis.risk_free_rate_annual * 100:.2f}% · "
        f"{metrics.n_obs} trading days · {metrics.start:%Y-%m-%d} to {metrics.end:%Y-%m-%d}"
    )

    stock_index_corr = float(analysis.stock_returns.corr(compute_log_returns(analysis.index_prices)))

    with _dashboard_section("1. Risk Level & Correlations"):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Risk level", classify_risk_level(metrics.annual_vol, capm.beta))
        c2.metric("Stock ↔ Index correlation", f"{stock_index_corr:.2f}")
        c3.metric("CAPM Beta", f"{capm.beta:.2f}")
        c4.metric("CAPM R²", f"{capm.r_squared:.2f}")

        if portfolio:
            _safe_chart(
                render_correlation_heatmap,
                "Asset Correlation Matrix",
                list(PORTFOLIO_ASSET_LABELS),
                portfolio.correlation_matrix.tolist(),
            )

    with _dashboard_section("2. Return Distribution"):
        if analysis.distribution:
            _safe_chart(
                render_distribution_chart,
                "Daily Log-Return Distribution (Stock)",
                analysis.distribution.bin_centers,
                analysis.distribution.counts,
                analysis.distribution.normal_x,
                analysis.distribution.normal_y,
            )

    with _dashboard_section("3. Monthly Return Probability (Gaussian)"):
        if analysis.gaussian:
            g1, g2, g3 = st.columns(3)
            g1.metric("Expected monthly return", f"{analysis.gaussian.expected_monthly_pct:+.2f}%")
            g2.metric("Probability of monthly loss", f"{analysis.gaussian.prob_loss * 100:.1f}%")
            g3.metric("5th percentile monthly return", f"{analysis.gaussian.worst_5pct_monthly_pct:.2f}%")
            _safe_chart(
                render_gaussian_risk_chart,
                "Gaussian Monthly Return Distribution",
                analysis.gaussian.x_pct,
                analysis.gaussian.density,
            )
            st.caption("X-axis: monthly return (loss ← 0 → profit). Y-axis: probability density.")

    with _dashboard_section("4. Downside Risk (5th Percentile)"):
        d1, d2, d3 = st.columns(3)
        d1.metric("Daily downside (5%)", f"-{metrics.daily_var_5 * 100:.2f}%")
        d2.metric("Annualized downside (5%)", f"-{metrics.annual_var_5 * 100:.2f}%")
        if analysis.gaussian:
            d3.metric("Monthly Gaussian downside (5%)", f"{analysis.gaussian.worst_5pct_monthly_pct:.2f}%")
        st.caption(
            "Historical 5% VaR: the daily loss exceeded only 5% of the time in the sample period."
        )

    with _dashboard_section("5. Price Forecast (STL + GARCH)"):
        if analysis.forecast:
            fc = analysis.forecast
            _safe_chart(
                render_line_chart,
                "STL Trend + GARCH Volatility Bands",
                fc.history_dates + fc.dates,
                [
                    {"name": "Historical price", "type": "line", "data": fc.history_prices + [None] * len(fc.dates), "lineStyle": {"width": 2}},
                    {"name": "Forecast (median)", "type": "line", "data": [None] * len(fc.history_dates) + [fc.history_prices[-1]] + fc.forecast_median, "lineStyle": {"width": 2, "type": "dashed"}},
                    {"name": "Upper band", "type": "line", "data": [None] * len(fc.history_dates) + [fc.history_prices[-1]] + fc.forecast_upper, "lineStyle": {"opacity": 0.4}},
                    {"name": "Lower band", "type": "line", "data": [None] * len(fc.history_dates) + [fc.history_prices[-1]] + fc.forecast_lower, "lineStyle": {"opacity": 0.4}, "areaStyle": {"opacity": 0.1, "color": "#5470c6"}},
                ],
                y_axis_name="Price",
                height=400,
            )
        else:
            st.warning("Not enough history for STL + GARCH forecast (about 120 trading days required).")

    with _dashboard_section("6. Stock Return"):
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Period return", f"{metrics.period_return * 100:+.2f}%")
        r2.metric("Annualized return", f"{metrics.annual_return * 100:+.2f}%")
        r3.metric("CAPM expected return", f"{capm.expected_return_capm * 100:+.2f}%")
        r4.metric("CAPM alpha (annual)", f"{capm.alpha_annual * 100:+.2f}%")

        price_dates = [d.strftime("%Y-%m-%d") for d in analysis.stock_prices.index]
        cumulative_return = ((analysis.stock_prices / analysis.stock_prices.iloc[0] - 1) * 100).tolist()
        _safe_chart(
            render_line_chart,
            "Cumulative Return (%)",
            price_dates,
            [{"name": "Cumulative return", "type": "line", "data": cumulative_return, "showSymbol": False}],
            y_axis_name="Return %",
        )

    with _dashboard_section("7. Rolling Annualized Volatility (3-year history)"):
        if not analysis.rolling_volatility.empty:
            vol_dates = [d.strftime("%Y-%m-%d") for d in analysis.rolling_volatility.index]
            _safe_chart(
                render_line_chart,
                f"Rolling {TRADING_DAYS_PER_YEAR}-day Annualized Volatility",
                vol_dates,
                [{"name": "Annualized vol", "type": "line", "data": (analysis.rolling_volatility * 100).tolist(), "showSymbol": False}],
                y_axis_name="Volatility %",
            )
            st.metric("Current annualized volatility", f"{metrics.annual_vol * 100:.2f}%")

    with _dashboard_section("8. Expected Return: Historical vs CAPM vs ML"):
        er = analysis.expected_returns
        if er is None:
            st.info("Expected-return comparison unavailable for this run.")
        else:
            stock_model = er.stock_model
            e1, e2, e3 = st.columns(3)
            e1.metric(
                "Historical mean (annual)",
                f"{_annualize_log_daily(er.stock_historical_daily) * 100:+.2f}%",
            )
            e2.metric("CAPM expected (annual)", f"{capm.expected_return_capm * 100:+.2f}%")
            e3.metric(
                f"ML forecast — {stock_model.model_name} (annual)",
                f"{_annualize_log_daily(er.stock_ml_daily) * 100:+.2f}%",
                help="Shrunk toward the historical mean and clipped for stability.",
            )

            if er.used_ml:
                cv_bits = []
                if stock_model.cv_mae is not None:
                    cv_bits.append(f"MAE {stock_model.cv_mae:.4f}")
                if stock_model.cv_rmse is not None:
                    cv_bits.append(f"RMSE {stock_model.cv_rmse:.4f}")
                if stock_model.cv_r2 is not None:
                    cv_bits.append(f"R² {stock_model.cv_r2:.3f}")
                cv_text = " · ".join(cv_bits) if cv_bits else "n/a"
                raw_annual = _annualize_log_daily(er.stock_ml_raw_daily) * 100
                baseline_text = ""
                if er.stock_baseline and er.stock_baseline.trained:
                    horizon = get_settings().ml_horizon_days
                    base_annual = (
                        _annualize_log_daily(er.stock_baseline.predicted_horizon_return / horizon) * 100
                    )
                    baseline_text = f" · Baseline {er.stock_baseline.model_name}: {base_annual:+.2f}% (raw)"
                st.caption(
                    f"Walk-forward CV ({stock_model.n_train_rows} rows): {cv_text}. "
                    f"Raw ML forecast {raw_annual:+.2f}% → shrunk {int(er.shrinkage * 100)}% toward history."
                    f"{baseline_text}"
                )

                if stock_model.feature_importance:
                    top = stock_model.feature_importance[:10]
                    _safe_chart(
                        render_feature_importance_chart,
                        f"Top Feature Importances — {stock_model.model_name}",
                        [name for name, _ in top],
                        [value for _, value in top],
                    )
            else:
                st.warning(
                    f"ML forecast unavailable ({stock_model.model_name}); "
                    "using historical mean as the expected return."
                )

    with _dashboard_section("Optimal Portfolio (Max Sharpe Ratio)"):
        if portfolio:
            if analysis.expected_returns and analysis.expected_returns.used_ml:
                st.caption(
                    "Optimization uses ML-informed expected returns (μ) with historical covariance. "
                    "Weights shift relative to the naive historical-mean optimization."
                )
            w1, w2, w3, w4 = st.columns(4)
            w1.metric("Expected return", f"{portfolio.expected_return_annual * 100:.2f}%")
            w2.metric("Portfolio volatility", f"{portfolio.volatility_annual * 100:.2f}%")
            w3.metric("Sharpe ratio", f"{portfolio.sharpe_ratio:.2f}")
            w4.metric("Risk-free weight", f"{portfolio.weights[2] * 100:.1f}%")

            _safe_chart(
                render_allocation_bar_chart,
                "Optimal Allocation Weights",
                list(PORTFOLIO_ASSET_LABELS),
                [round(weight * 100, 1) for weight in portfolio.weights],
            )

            if len(portfolio.frontier_vol) > 2:
                _safe_chart(
                    render_efficient_frontier_chart,
                    "Efficient Frontier vs Optimal Portfolio",
                    (portfolio.frontier_vol * 100).tolist(),
                    (portfolio.frontier_ret * 100).tolist(),
                    portfolio.asset_stats[:2],
                    {"vol": portfolio.volatility_annual, "return": portfolio.expected_return_annual},
                )

            _safe_chart(
                render_capm_line_chart,
                analysis.risk_free_rate_annual,
                capm.expected_return_capm,
                capm.beta,
                metrics.annual_return,
            )
