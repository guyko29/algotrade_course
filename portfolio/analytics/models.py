"""Analytics result models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd


@dataclass
class StockMetrics:
    n_obs: int
    start: datetime
    end: datetime
    last_price: float
    period_return: float
    annual_return: float
    annual_vol: float
    daily_var_5: float
    annual_var_5: float


@dataclass
class CapmResult:
    beta: float
    alpha_daily: float
    alpha_annual: float
    r_squared: float
    expected_return_capm: float


@dataclass
class PortfolioResult:
    weights: np.ndarray
    expected_return_annual: float
    volatility_annual: float
    sharpe_ratio: float
    correlation_matrix: np.ndarray
    frontier_vol: np.ndarray
    frontier_ret: np.ndarray
    asset_stats: list[dict]


@dataclass
class DistributionResult:
    bin_centers: list[float]
    counts: list[int]
    normal_x: list[float]
    normal_y: list[float]


@dataclass
class MonthlyGaussianResult:
    x_pct: list[float]
    density: list[float]
    prob_loss: float
    expected_monthly_pct: float
    worst_5pct_monthly_pct: float


@dataclass
class PriceForecastResult:
    dates: list[str]
    history_dates: list[str]
    history_prices: list[float]
    forecast_median: list[float]
    forecast_lower: list[float]
    forecast_upper: list[float]
    trend_component: list[float]


@dataclass
class PortfolioAnalysis:
    stock_id: int
    benchmark_id: int
    benchmark_requested: int
    risk_free_rate_annual: float
    stock_prices: pd.Series
    index_prices: pd.Series
    stock_returns: pd.Series
    metrics: StockMetrics
    capm: CapmResult
    portfolio: PortfolioResult | None
    distribution: DistributionResult | None
    gaussian: MonthlyGaussianResult | None
    forecast: PriceForecastResult | None
    rolling_volatility: pd.Series
