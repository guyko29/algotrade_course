"""Single entry point for expected returns: historical vs CAPM vs ML.

Produces the expected daily-return vector that Markowitz consumes. The ML drift
is deliberately *shrunk* toward the historical mean and clipped to a sane band:
a raw next-month point forecast is far too noisy to use directly as ``μ`` and can
push the optimizer into degenerate corner solutions. Shrinkage keeps the optimal
weights stable while still letting the ML signal tilt the allocation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from portfolio.analytics.features import build_feature_matrix
from portfolio.analytics.ml_forecast import train_return_model
from portfolio.analytics.models import CapmResult, ExpectedReturnsResult, MlForecastResult
from portfolio.config import Settings, get_settings
from portfolio.constants import TRADING_DAYS_PER_YEAR
from portfolio.logger import get_logger

logger = get_logger(__name__)

# Clip the (shrunk) ML drift so the annualized log return stays within ±60%.
_MAX_ANNUAL_LOG_RETURN = 0.60
_MAX_DAILY_LOG_RETURN = _MAX_ANNUAL_LOG_RETURN / TRADING_DAYS_PER_YEAR


def _horizon_to_daily(result: MlForecastResult, horizon: int) -> float:
    """Convert a predicted horizon log return into a per-day log return."""
    if not result.trained or horizon <= 0:
        return float("nan")
    return result.predicted_horizon_return / horizon


def _shrink_and_clip(ml_daily: float, historical_daily: float, shrinkage: float) -> float:
    """Blend ML toward the historical mean, then clip to the sane daily band."""
    if np.isnan(ml_daily):
        return historical_daily
    blended = shrinkage * ml_daily + (1.0 - shrinkage) * historical_daily
    return float(np.clip(blended, -_MAX_DAILY_LOG_RETURN, _MAX_DAILY_LOG_RETURN))


def build_expected_returns(
    stock_prices: pd.Series,
    index_prices: pd.Series,
    stock_returns: pd.Series,
    index_returns: pd.Series,
    capm_result: CapmResult,
    settings: Settings | None = None,
) -> ExpectedReturnsResult:
    """Train ML drift models and assemble the historical/CAPM/ML comparison.

    Always returns a result: when ML is unavailable the ML columns fall back to
    the historical mean and ``used_ml`` is ``False``.
    """
    settings = settings or get_settings()
    horizon = settings.ml_horizon_days
    shrinkage = settings.ml_shrinkage

    stock_historical_daily = float(stock_returns.mean())
    index_historical_daily = float(index_returns.mean())
    # CAPM expected return is annual & simple; express as an equivalent daily log return.
    stock_capm_daily = float(np.log1p(capm_result.expected_return_capm) / TRADING_DAYS_PER_YEAR)

    # --- Stock: primary model + interpretable baseline ---
    stock_matrix = build_feature_matrix(stock_prices, index_prices, horizon)
    stock_model = train_return_model(stock_matrix, settings.ml_model, settings.ml_min_train_rows)

    baseline_type = "ridge" if settings.ml_model != "ridge" else "linear"
    stock_baseline = train_return_model(stock_matrix, baseline_type, settings.ml_min_train_rows)

    stock_ml_raw_daily = _horizon_to_daily(stock_model, horizon)
    stock_ml_daily = _shrink_and_clip(stock_ml_raw_daily, stock_historical_daily, shrinkage)

    # --- Index: same primary model so Markowitz gets an ML drift for both assets ---
    index_matrix = build_feature_matrix(index_prices, None, horizon)
    index_model = train_return_model(index_matrix, settings.ml_model, settings.ml_min_train_rows)
    index_ml_raw_daily = _horizon_to_daily(index_model, horizon)
    index_ml_daily = _shrink_and_clip(index_ml_raw_daily, index_historical_daily, shrinkage)

    used_ml = stock_model.trained

    logger.info(
        "Expected returns | historical=%.5f capm=%.5f ml_raw=%.5f ml_used=%.5f (shrink=%.2f, used_ml=%s)",
        stock_historical_daily,
        stock_capm_daily,
        stock_ml_raw_daily,
        stock_ml_daily,
        shrinkage,
        used_ml,
    )

    return ExpectedReturnsResult(
        stock_historical_daily=stock_historical_daily,
        index_historical_daily=index_historical_daily,
        stock_capm_daily=stock_capm_daily,
        stock_ml_raw_daily=stock_ml_raw_daily,
        stock_ml_daily=stock_ml_daily,
        index_ml_daily=index_ml_daily,
        shrinkage=shrinkage,
        used_ml=used_ml,
        stock_model=stock_model,
        stock_baseline=stock_baseline,
        index_model=index_model,
    )


def markowitz_asset_vector(result: ExpectedReturnsResult) -> np.ndarray:
    """The [stock, index] daily expected-return vector Markowitz should optimize over."""
    return np.array([result.stock_ml_daily, result.index_ml_daily])
