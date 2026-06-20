"""
TASE Optimal Portfolio Analyzer — Streamlit entrypoint.

Run locally:
    streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from portfolio.logger import setup_logging
from portfolio.ui import (
    init_session_state,
    render_dashboard_page,
    render_landing_page,
    render_sidebar,
)

setup_logging()

st.set_page_config(
    page_title="TASE Optimal Portfolio",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()

if st.session_state.page == "landing":
    render_landing_page()
    sidebar = render_sidebar(show_dashboard_actions=False)
    if sidebar.analyze_clicked and sidebar.stock_id is not None:
        st.session_state.stock_id = sidebar.stock_id
        st.session_state.stock_query = sidebar.stock_query
        st.session_state.stock_label = sidebar.stock_label
        st.session_state.benchmark_id = sidebar.benchmark_id
        st.session_state.risk_free_rate_annual = sidebar.risk_free_rate_annual
        st.session_state.page = "dashboard"
        st.session_state.loading = True
        st.session_state.force_reload = True
        st.rerun()
else:
    sidebar = render_sidebar(show_dashboard_actions=True)
    if sidebar.back_clicked:
        st.session_state.page = "landing"
        st.session_state.loading = False
        st.session_state.pop("disambiguation_query", None)
        st.rerun()
    if sidebar.reload_clicked:
        st.session_state.loading = True
        st.session_state.force_reload = True
        st.rerun()

    render_dashboard_page(
        stock_id=int(st.session_state.stock_id),
        benchmark_id=sidebar.benchmark_id,
        risk_free_rate_annual=sidebar.risk_free_rate_annual,
    )
