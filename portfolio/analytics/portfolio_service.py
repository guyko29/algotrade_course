"""Orchestrates data fetching and portfolio analytics."""

from __future__ import annotations

from datetime import date
from typing import Callable, Optional

from portfolio.analytics.capm import calculate_capm
from portfolio.analytics.expected_returns import build_expected_returns, markowitz_asset_vector
from portfolio.analytics.forecast import forecast_price_stl_garch
from portfolio.analytics.markowitz import optimize_max_sharpe_portfolio
from portfolio.analytics.models import PortfolioAnalysis
from portfolio.analytics.prices import align_price_series, compute_log_returns, parse_close_price_series
from portfolio.analytics.risk_metrics import (
    calculate_monthly_gaussian_risk,
    calculate_return_distribution,
    calculate_rolling_annualized_volatility,
    calculate_stock_metrics,
)
from portfolio.config import get_settings
from portfolio.data.tase_client import ProgressCallback, TaseClient
from portfolio.errors import InsufficientDataError
from portfolio.logger import get_logger

logger = get_logger(__name__)


class PortfolioAnalysisService:
    """Build a complete portfolio analysis for one TASE security."""

    def __init__(self, client: TaseClient | None = None) -> None:
        self._client = client or TaseClient()
        self._settings = get_settings()

    def build_analysis(
        self,
        stock_id: int,
        benchmark_id: int,
        risk_free_rate_annual: float,
        on_progress: Callable[[float, str], None] | None = None,
    ) -> PortfolioAnalysis:
        today = date.today()
        start = date(
            today.year - self._settings.lookback_years,
            today.month,
            min(today.day, 28),
        )

        def wrap_progress(base: float, span: float, label: str) -> ProgressCallback:
            def callback(message: str, fraction: float | None) -> None:
                if on_progress:
                    frac = base + span * (fraction if fraction is not None else 0.5)
                    on_progress(frac, f"{label}: {message}")
            return callback

        logger.info(
            "Starting analysis stock_id=%s benchmark_id=%s rf=%.4f",
            stock_id,
            benchmark_id,
            risk_free_rate_annual,
        )

        if on_progress:
            on_progress(0.02, "Connecting to TASE — fetching stock history (30–60 sec)...")

        stock_rows = self._client.fetch_security_history(
            stock_id,
            start,
            today,
            wrap_progress(0.05, 0.40, "Stock data"),
        )

        if on_progress:
            on_progress(0.48, "Fetching benchmark index...")

        index_rows, benchmark_used = self._client.fetch_benchmark_with_fallback(
            benchmark_id,
            start,
            today,
            wrap_progress(0.48, 0.35, "Benchmark"),
        )

        if on_progress:
            on_progress(0.88, "Computing portfolio analytics...")

        stock_prices = parse_close_price_series(stock_rows)
        index_prices = parse_close_price_series(index_rows)
        aligned = align_price_series(stock_prices, index_prices)

        if len(aligned) < self._settings.min_overlapping_trading_days:
            raise InsufficientDataError(
                f"Only {len(aligned)} overlapping days; "
                f"need {self._settings.min_overlapping_trading_days}"
            )

        stock_prices = aligned.iloc[:, 0]
        index_prices = aligned.iloc[:, 1]
        stock_returns = compute_log_returns(stock_prices)
        index_returns = compute_log_returns(index_prices)

        metrics = calculate_stock_metrics(stock_prices)
        if metrics is None:
            raise InsufficientDataError("Could not compute stock metrics")

        capm = calculate_capm(stock_returns, index_returns, risk_free_rate_annual)

        if on_progress:
            on_progress(0.92, "Training ML return forecast...")

        expected_returns = build_expected_returns(
            stock_prices=stock_prices,
            index_prices=index_prices,
            stock_returns=stock_returns,
            index_returns=index_returns,
            capm_result=capm,
            settings=self._settings,
        )
        asset_mu = markowitz_asset_vector(expected_returns) if expected_returns.used_ml else None

        analysis = PortfolioAnalysis(
            stock_id=stock_id,
            benchmark_id=benchmark_used,
            benchmark_requested=benchmark_id,
            risk_free_rate_annual=risk_free_rate_annual,
            stock_prices=stock_prices,
            index_prices=index_prices,
            stock_returns=stock_returns,
            metrics=metrics,
            capm=capm,
            portfolio=optimize_max_sharpe_portfolio(
                stock_returns, index_returns, risk_free_rate_annual, asset_mu
            ),
            distribution=calculate_return_distribution(stock_returns),
            gaussian=calculate_monthly_gaussian_risk(
                stock_returns,
                expected_returns.stock_ml_daily if expected_returns.used_ml else None,
            ),
            forecast=forecast_price_stl_garch(stock_prices),
            rolling_volatility=calculate_rolling_annualized_volatility(stock_returns).dropna(),
            expected_returns=expected_returns,
        )

        logger.info(
            "Analysis complete stock_id=%s days=%s sharpe=%s",
            stock_id,
            metrics.n_obs,
            analysis.portfolio.sharpe_ratio if analysis.portfolio else "n/a",
        )

        if on_progress:
            on_progress(1.0, "Done — rendering dashboard...")

        return analysis
