"""
Financial analytics for a TASE index price series.

All metrics are derived from the daily closing prices (``CloseRate``).
Functions are pure: they take prices/returns and return numbers or
DataFrames, with no dependency on Streamlit.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd

# Trading days in a year — used to annualize daily statistics.
TRADING_DAYS = 252


def to_price_series(items: list) -> pd.Series:
    """Turn raw scraper rows into a date-indexed close-price Series (ascending)."""
    rows = []
    for r in items:
        close = r.get("CloseRate")
        td = r.get("TradeDate")
        if close is None or td is None:
            continue
        rows.append((datetime.strptime(td, "%d/%m/%Y"), float(close)))
    if not rows:
        return pd.Series(dtype=float)
    s = pd.Series(dict(rows)).sort_index()
    s.index.name = "TradeDate"
    s.name = "Close"
    return s


def log_returns(prices: pd.Series) -> pd.Series:
    """Daily log returns r_t = ln(P_t / P_{t-1})."""
    return np.log(prices / prices.shift(1)).dropna()


@dataclass
class Metrics:
    n_obs: int                 # number of trading days
    start: datetime
    end: datetime
    last_price: float
    period_return: float       # total return over the window
    annual_return: float       # annualized (CAGR-style, from mean log return)
    annual_vol: float          # annualized standard deviation (volatility)
    daily_var_5: float         # historical 1-day Value-at-Risk at 95% (positive = loss)
    annual_var_5: float        # the same scaled to one year (sqrt-of-time)


def compute_metrics(prices: pd.Series) -> Metrics | None:
    """Core dashboard metrics. Returns None if there isn't enough data."""
    if len(prices) < 3:
        return None

    rets = log_returns(prices)
    if rets.empty:
        return None

    daily_mean = float(rets.mean())
    daily_std = float(rets.std(ddof=1))

    annual_vol = daily_std * np.sqrt(TRADING_DAYS)
    annual_return = np.expm1(daily_mean * TRADING_DAYS)
    period_return = float(prices.iloc[-1] / prices.iloc[0] - 1.0)

    # Historical VaR at 5%: the 5th percentile of daily returns is the loss
    # that is exceeded only 5% of the time. Report it as a positive magnitude.
    daily_var_5 = float(-np.percentile(rets, 5))
    annual_var_5 = daily_var_5 * np.sqrt(TRADING_DAYS)

    return Metrics(
        n_obs=len(prices),
        start=prices.index[0].to_pydatetime(),
        end=prices.index[-1].to_pydatetime(),
        last_price=float(prices.iloc[-1]),
        period_return=period_return,
        annual_return=annual_return,
        annual_vol=annual_vol,
        daily_var_5=daily_var_5,
        annual_var_5=annual_var_5,
    )


@dataclass
class Forecast:
    horizon: int               # trading days projected forward
    paths: np.ndarray          # shape (n_sims, horizon + 1), includes day 0
    dates: pd.DatetimeIndex    # future business dates aligned to columns
    median: np.ndarray
    p5: np.ndarray
    p95: np.ndarray
    final_prices: np.ndarray   # simulated price on the last horizon day
    exp_price: float           # median final price
    exp_return: float          # median return vs. last observed price
    downside_5_price: float    # 5th percentile final price
    downside_5_return: float   # corresponding return (negative = loss)


def monte_carlo_forecast(
    prices: pd.Series,
    horizon: int,
    n_sims: int = 2000,
    seed: int = 42,
) -> Forecast | None:
    """
    Geometric-Brownian-Motion Monte Carlo forecast.

    Daily log returns are modeled as Normal(mu, sigma) estimated from history.
    Each simulated path compounds ``horizon`` daily draws forward from the last
    observed price. The spread of the simulated paths is the forecast's
    uncertainty; the 5th percentile of the final prices is the 5% downside.
    """
    rets = log_returns(prices)
    if rets.empty or horizon < 1:
        return None

    mu = float(rets.mean())
    sigma = float(rets.std(ddof=1))
    s0 = float(prices.iloc[-1])

    rng = np.random.default_rng(seed)
    # Draw (n_sims x horizon) daily log returns, compound them cumulatively.
    shocks = rng.normal(mu, sigma, size=(n_sims, horizon))
    cum = np.cumsum(shocks, axis=1)
    paths = s0 * np.exp(np.concatenate([np.zeros((n_sims, 1)), cum], axis=1))

    median = np.median(paths, axis=0)
    p5 = np.percentile(paths, 5, axis=0)
    p95 = np.percentile(paths, 95, axis=0)

    final_prices = paths[:, -1]
    exp_price = float(np.median(final_prices))
    downside_5_price = float(np.percentile(final_prices, 5))

    last_date = prices.index[-1]
    future_dates = pd.bdate_range(start=last_date, periods=horizon + 1)

    return Forecast(
        horizon=horizon,
        paths=paths,
        dates=future_dates,
        median=median,
        p5=p5,
        p95=p95,
        final_prices=final_prices,
        exp_price=exp_price,
        exp_return=exp_price / s0 - 1.0,
        downside_5_price=downside_5_price,
        downside_5_return=downside_5_price / s0 - 1.0,
    )
