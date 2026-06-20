"""Shared financial and market constants."""

from __future__ import annotations

TRADING_DAYS_PER_YEAR = 252
MONTHLY_TRADING_DAYS = 21

TA35_INDEX_ID = 142
TA125_INDEX_ID = 146

BENCHMARK_OPTIONS = {
    "TA35": TA35_INDEX_ID,
    "TA-35": TA35_INDEX_ID,
    "TA125": TA125_INDEX_ID,
    "TA-125": TA125_INDEX_ID,
}

PORTFOLIO_ASSET_LABELS = ("Stock", "Market Index", "Risk-Free")

DEFAULT_STOCK_QUERY = "ESLT"
