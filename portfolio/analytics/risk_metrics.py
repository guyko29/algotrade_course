"""Risk metrics and stock performance statistics."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

from portfolio.analytics.models import DistributionResult, MonthlyGaussianResult, StockMetrics
from portfolio.analytics.prices import compute_log_returns
from portfolio.constants import MONTHLY_TRADING_DAYS, TRADING_DAYS_PER_YEAR


def calculate_stock_metrics(prices: pd.Series) -> StockMetrics | None:
    if len(prices) < 3:
        return None

    returns = compute_log_returns(prices)
    if returns.empty:
        return None

    daily_std = float(returns.std(ddof=1))
    daily_mean = float(returns.mean())

    return StockMetrics(
        n_obs=len(prices),
        start=prices.index[0].to_pydatetime(),
        end=prices.index[-1].to_pydatetime(),
        last_price=float(prices.iloc[-1]),
        period_return=float(prices.iloc[-1] / prices.iloc[0] - 1.0),
        annual_return=float(np.expm1(daily_mean * TRADING_DAYS_PER_YEAR)),
        annual_vol=daily_std * np.sqrt(TRADING_DAYS_PER_YEAR),
        daily_var_5=float(-np.percentile(returns, 5)),
        annual_var_5=float(-np.percentile(returns, 5)) * np.sqrt(TRADING_DAYS_PER_YEAR),
    )


def classify_risk_level(annual_volatility: float, beta: float) -> str:
    score = annual_volatility * 0.6 + min(abs(beta), 2.0) * 0.2
    if score < 0.18:
        return "Low"
    if score < 0.30:
        return "Medium"
    return "High"


def calculate_return_distribution(returns: pd.Series, bins: int = 30) -> DistributionResult | None:
    if returns.empty:
        return None

    histogram, edges = np.histogram(returns.values * 100, bins=bins, density=True)
    centers = [float((edges[i] + edges[i + 1]) / 2) for i in range(len(histogram))]
    counts = [int(value) for value in (histogram * len(returns) * (edges[1] - edges[0])).tolist()]

    mean_pct = float(returns.mean() * 100)
    std_pct = float(returns.std(ddof=1) * 100)
    xs = np.linspace(edges[0], edges[-1], 200)
    ys = norm.pdf(xs, mean_pct, std_pct).tolist()

    return DistributionResult(bin_centers=centers, counts=counts, normal_x=xs.tolist(), normal_y=ys)


def calculate_monthly_gaussian_risk(returns: pd.Series) -> MonthlyGaussianResult | None:
    if returns.empty:
        return None

    monthly_mean = float(returns.mean() * MONTHLY_TRADING_DAYS)
    monthly_std = float(returns.std(ddof=1) * np.sqrt(MONTHLY_TRADING_DAYS))
    xs = np.linspace(monthly_mean - 4 * monthly_std, monthly_mean + 4 * monthly_std, 200)
    density = norm.pdf(xs, monthly_mean, monthly_std)

    return MonthlyGaussianResult(
        x_pct=(xs * 100).tolist(),
        density=density.tolist(),
        prob_loss=float(norm.cdf(0.0, monthly_mean, monthly_std)),
        expected_monthly_pct=monthly_mean * 100,
        worst_5pct_monthly_pct=float(norm.ppf(0.05, monthly_mean, monthly_std)) * 100,
    )


def calculate_rolling_annualized_volatility(
    returns: pd.Series,
    window: int = TRADING_DAYS_PER_YEAR,
) -> pd.Series:
    if returns.empty:
        return pd.Series(dtype=float)
    return returns.rolling(window).std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)
