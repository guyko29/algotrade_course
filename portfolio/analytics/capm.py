"""CAPM analytics."""

from __future__ import annotations

import numpy as np
import pandas as pd

from portfolio.analytics.models import CapmResult
from portfolio.constants import TRADING_DAYS_PER_YEAR


def calculate_capm(
    stock_returns: pd.Series,
    market_returns: pd.Series,
    risk_free_rate_annual: float,
) -> CapmResult:
    aligned = pd.concat([stock_returns, market_returns], axis=1, join="inner").dropna()
    aligned.columns = ["stock", "market"]

    risk_free_daily = risk_free_rate_annual / TRADING_DAYS_PER_YEAR
    excess_stock = aligned["stock"] - risk_free_daily
    excess_market = aligned["market"] - risk_free_daily

    covariance = np.cov(excess_stock, excess_market, ddof=1)
    beta = float(covariance[0, 1] / covariance[1, 1]) if covariance[1, 1] > 0 else 0.0
    alpha_daily = float(excess_stock.mean() - beta * excess_market.mean())
    alpha_annual = alpha_daily * TRADING_DAYS_PER_YEAR

    correlation = np.corrcoef(excess_stock, excess_market)[0, 1]
    r_squared = float(correlation ** 2) if not np.isnan(correlation) else 0.0
    market_premium_annual = float(excess_market.mean() * TRADING_DAYS_PER_YEAR)

    return CapmResult(
        beta=beta,
        alpha_daily=alpha_daily,
        alpha_annual=alpha_annual,
        r_squared=r_squared,
        expected_return_capm=risk_free_rate_annual + beta * market_premium_annual,
    )
