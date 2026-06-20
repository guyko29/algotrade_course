"""Technical-indicator feature engineering for return forecasting.

Turns aligned close-price series into a supervised learning matrix whose target
is the *next* ``horizon``-day log return. All features are causal (computed only
from past/current prices) so the matrix is free of look-ahead leakage; the target
is shifted backwards by ``horizon`` and the final ``horizon`` rows (which would
need future prices) are dropped.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TARGET_COLUMN = "next_log_return"


def _rsi(prices: pd.Series, window: int = 14) -> pd.Series:
    delta = prices.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    return 100.0 - 100.0 / (1.0 + rs)


def _macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    # Normalize by price so the feature is scale-free across securities.
    return (macd_line - signal_line) / prices


def build_feature_matrix(
    prices: pd.Series,
    index_prices: pd.Series | None = None,
    horizon: int = 21,
) -> pd.DataFrame:
    """Build a causal feature/target matrix for next-``horizon``-day returns.

    Returns a DataFrame whose last column is :data:`TARGET_COLUMN`. Rows with any
    NaN (warm-up periods, trailing target gap) are dropped.
    """
    if len(prices) < horizon + 30:
        return pd.DataFrame()

    log_price = np.log(prices)
    log_return = log_price.diff()

    features = pd.DataFrame(index=prices.index)

    # 1. Lagged daily log returns (short-term autocorrelation signal).
    features["ret_lag_1"] = log_return.shift(1)
    features["ret_lag_5"] = log_return.shift(1).rolling(5).sum()
    features["ret_lag_21"] = log_return.shift(1).rolling(21).sum()

    # 2. Realized volatility (21-day rolling std of daily returns).
    features["vol_21"] = log_return.rolling(21).std(ddof=1)

    # 3. Momentum: price relative to its own moving averages.
    sma_21 = prices.rolling(21).mean()
    ema_50 = prices.ewm(span=50, adjust=False).mean()
    features["sma_21_ratio"] = prices / sma_21 - 1.0
    features["ema_50_ratio"] = prices / ema_50 - 1.0
    features["momentum_21"] = prices / prices.shift(21) - 1.0

    # 4. RSI(14) — overbought/oversold oscillator, scaled to [0, 1].
    features["rsi_14"] = _rsi(prices, 14) / 100.0

    # 5. MACD histogram (normalized by price).
    features["macd_hist"] = _macd(prices)

    # 6. Optional market-index context (its own short momentum).
    if index_prices is not None:
        index_log_return = np.log(index_prices).diff()
        features["index_ret_lag_1"] = index_log_return.shift(1)
        features["index_momentum_21"] = index_prices / index_prices.shift(21) - 1.0

    # Target: forward horizon-day log return (shifted back so each row predicts ahead).
    features[TARGET_COLUMN] = log_price.shift(-horizon) - log_price

    return features.dropna()


def feature_columns(matrix: pd.DataFrame) -> list[str]:
    return [column for column in matrix.columns if column != TARGET_COLUMN]
