"""Price series utilities."""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd


def parse_close_price_series(rows: list[dict]) -> pd.Series:
    """Convert TASE EOD rows into an ascending close-price series."""
    parsed: list[tuple[datetime, float]] = []
    for row in rows:
        close = row.get("CloseRate")
        trade_date = row.get("TradeDate")
        if close is None or trade_date is None:
            continue
        parsed.append((datetime.strptime(trade_date, "%d/%m/%Y"), float(close)))

    if not parsed:
        return pd.Series(dtype=float)

    series = pd.Series(dict(parsed)).sort_index()
    series.index.name = "TradeDate"
    series.name = "Close"
    return series


def compute_log_returns(prices: pd.Series) -> pd.Series:
    return np.log(prices / prices.shift(1)).dropna()


def align_price_series(*series: pd.Series) -> pd.DataFrame:
    return pd.concat(series, axis=1, join="inner").dropna().sort_index()
