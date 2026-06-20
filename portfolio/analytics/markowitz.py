"""Markowitz portfolio optimization."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from portfolio.analytics.models import PortfolioResult
from portfolio.constants import PORTFOLIO_ASSET_LABELS, TRADING_DAYS_PER_YEAR


def _annualize_return(daily_mean: float) -> float:
    return float(np.expm1(daily_mean * TRADING_DAYS_PER_YEAR))


def _annualize_volatility(daily_std: float) -> float:
    return float(daily_std * np.sqrt(TRADING_DAYS_PER_YEAR))


def _efficient_frontier_curve(
    aligned: pd.DataFrame,
    n_points: int = 40,
) -> tuple[np.ndarray, np.ndarray]:
    mu = aligned.mean().values
    cov = aligned.cov().values
    n_assets = len(mu)

    def portfolio_stats(weights: np.ndarray) -> tuple[float, float]:
        ret = weights @ mu
        vol = np.sqrt(max(weights @ cov @ weights, 1e-18))
        return ret, vol

    def min_vol_for_target(target: float) -> tuple[float, float]:
        def objective(weights: np.ndarray) -> float:
            return weights @ cov @ weights

        constraints = (
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
            {"type": "eq", "fun": lambda w: w @ mu - target},
        )
        bounds = [(0.0, 1.0)] * n_assets
        initial = np.ones(n_assets) / n_assets
        result = minimize(objective, initial, method="SLSQP", bounds=bounds, constraints=constraints)
        if result.success:
            return portfolio_stats(result.x)
        return target, np.nan

    targets = np.linspace(mu.min(), mu.max(), n_points)
    vols, returns = [], []
    for target in targets:
        daily_return, daily_vol = min_vol_for_target(float(target))
        if not np.isnan(daily_vol):
            vols.append(_annualize_volatility(daily_vol))
            returns.append(_annualize_return(daily_return))

    return np.array(vols), np.array(returns)


def optimize_max_sharpe_portfolio(
    stock_returns: pd.Series,
    index_returns: pd.Series,
    risk_free_rate_annual: float,
    asset_expected_daily_returns: np.ndarray | None = None,
) -> PortfolioResult | None:
    """Optimize the max-Sharpe portfolio over [Stock, Index, Risk-Free].

    When ``asset_expected_daily_returns`` (a length-2 ``[stock, index]`` vector,
    e.g. ML-informed drift) is provided it replaces the historical sample means as
    the expected-return inputs; the risk-free leg is always the supplied rate.
    Covariance and the efficient frontier always use the historical sample.
    """
    aligned = pd.concat([stock_returns, index_returns], axis=1, join="inner").dropna()
    if len(aligned) < 30:
        return None

    aligned.columns = ["stock", "index"]
    risk_free_daily = risk_free_rate_annual / TRADING_DAYS_PER_YEAR

    if asset_expected_daily_returns is not None:
        stock_mu, index_mu = float(asset_expected_daily_returns[0]), float(asset_expected_daily_returns[1])
    else:
        stock_mu, index_mu = float(aligned["stock"].mean()), float(aligned["index"].mean())

    expected_daily_returns = np.array([stock_mu, index_mu, risk_free_daily])
    covariance_2x2 = aligned.cov().values
    covariance = np.zeros((3, 3))
    covariance[:2, :2] = covariance_2x2

    correlation = np.eye(3)
    correlation[:2, :2] = aligned.corr().values

    def negative_sharpe(weights: np.ndarray) -> float:
        port_return = weights @ expected_daily_returns
        port_vol = np.sqrt(max(weights @ covariance @ weights, 1e-18))
        return -(port_return - risk_free_daily) / port_vol * np.sqrt(TRADING_DAYS_PER_YEAR)

    constraints = ({"type": "eq", "fun": lambda w: np.sum(w) - 1.0},)
    bounds = [(0.0, 1.0)] * 3
    initial_weights = np.array([1 / 3, 1 / 3, 1 / 3])
    result = minimize(negative_sharpe, initial_weights, method="SLSQP", bounds=bounds, constraints=constraints)
    weights = result.x if result.success else initial_weights

    port_return_daily = float(weights @ expected_daily_returns)
    port_vol_daily = float(np.sqrt(max(weights @ covariance @ weights, 1e-18)))
    sharpe = (port_return_daily - risk_free_daily) / port_vol_daily * np.sqrt(TRADING_DAYS_PER_YEAR)
    frontier_vol, frontier_ret = _efficient_frontier_curve(aligned)

    asset_stats = [
        {
            "name": PORTFOLIO_ASSET_LABELS[0],
            "return": _annualize_return(stock_mu),
            "vol": _annualize_volatility(float(aligned["stock"].std(ddof=1))),
        },
        {
            "name": PORTFOLIO_ASSET_LABELS[1],
            "return": _annualize_return(index_mu),
            "vol": _annualize_volatility(float(aligned["index"].std(ddof=1))),
        },
        {
            "name": PORTFOLIO_ASSET_LABELS[2],
            "return": risk_free_rate_annual,
            "vol": 0.0,
        },
    ]

    return PortfolioResult(
        weights=weights,
        expected_return_annual=_annualize_return(port_return_daily),
        volatility_annual=_annualize_volatility(port_vol_daily),
        sharpe_ratio=float(sharpe),
        correlation_matrix=correlation,
        frontier_vol=frontier_vol,
        frontier_ret=frontier_ret,
        asset_stats=asset_stats,
    )
