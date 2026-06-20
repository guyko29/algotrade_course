"""Streamlit session state helpers."""

from __future__ import annotations

import streamlit as st

from portfolio.config import get_settings
from portfolio.constants import DEFAULT_STOCK_QUERY, TA125_INDEX_ID, TA35_INDEX_ID


def init_session_state() -> None:
    settings = get_settings()
    defaults = {
        "page": "landing",
        "stock_id": 1081124,
        "stock_query": DEFAULT_STOCK_QUERY,
        "stock_label": "ELBIT SYSTEMS (ESLT)",
        "benchmark_id": TA35_INDEX_ID if settings.default_benchmark != "TA125" else TA125_INDEX_ID,
        "risk_free_rate_annual": settings.default_risk_free_rate_annual,
        "loading": False,
        "force_reload": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def should_reload_analysis(stock_id: int, benchmark_id: int, risk_free_rate_annual: float) -> bool:
    if st.session_state.get("force_reload"):
        return True
    if "analysis" not in st.session_state:
        return True
    analysis = st.session_state.analysis
    return (
        st.session_state.get("loaded_stock_id") != stock_id
        or analysis.benchmark_requested != benchmark_id
        or abs(analysis.risk_free_rate_annual - risk_free_rate_annual) > 1e-9
    )
