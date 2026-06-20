"""Sidebar controls — stock input, settings, and navigation."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from portfolio.constants import DEFAULT_STOCK_QUERY, TA125_INDEX_ID, TA35_INDEX_ID
from portfolio.data.security_resolver import pick_security_match, search_securities
from portfolio.errors import DataFetchError, display_error


@dataclass
class SidebarAction:
    stock_id: int | None
    stock_query: str
    stock_label: str
    benchmark_id: int
    risk_free_rate_annual: float
    analyze_clicked: bool
    reload_clicked: bool
    back_clicked: bool


def _inject_sidebar_styles() -> None:
    st.markdown(
        """
        <style>
        .sidebar-muted-hint {
            font-size: 0.72rem;
            color: #9aa0a6;
            line-height: 1.35;
            margin: 0.15rem 0 0.5rem 0;
        }
        .sidebar-load-hint {
            font-size: 0.78rem;
            color: #5f6368;
            line-height: 1.4;
            margin: 0.35rem 0 0.75rem 0;
        }
        .sidebar-section-gap {
            margin-top: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_advanced_settings() -> tuple[int, float]:
    with st.expander("Advanced settings", expanded=False):
        benchmark_label = st.selectbox(
            "Market benchmark",
            options=["TA-35", "TA-125"],
            index=0 if st.session_state.benchmark_id == TA35_INDEX_ID else 1,
        )
        benchmark_id = TA35_INDEX_ID if benchmark_label == "TA-35" else TA125_INDEX_ID
        risk_free_rate_annual = (
            st.number_input(
                "Risk-free rate (annual %)",
                min_value=0.0,
                max_value=20.0,
                value=float(st.session_state.risk_free_rate_annual) * 100,
                step=0.1,
            )
            / 100.0
        )
    return benchmark_id, risk_free_rate_annual


def _resolve_stock_selection(
    stock_query: str,
) -> tuple[int | None, str, bool]:
    """Return (stock_id, stock_label, ready_to_analyze)."""
    disambiguation_query = st.session_state.get("disambiguation_query")
    if disambiguation_query:
        try:
            matches = search_securities(disambiguation_query, limit=12)
        except DataFetchError as exc:
            display_error(st, exc)
            return None, "", False

        if not matches:
            st.session_state.pop("disambiguation_query", None)
            st.error("No matching stock was found. Try a different name or symbol.")
            return None, "", False

        st.warning("Multiple stocks match your search. Please choose one:")
        selected = st.selectbox(
            "Select stock",
            options=matches,
            format_func=lambda record: record.display_label,
            label_visibility="collapsed",
        )
        if st.button("Continue with selected stock →", type="primary", use_container_width=True):
            st.session_state.pop("disambiguation_query", None)
            return selected.security_id, selected.display_label, True
        return None, "", False

    try:
        matches = search_securities(stock_query, limit=12)
    except DataFetchError as exc:
        display_error(st, exc)
        return None, "", False

    if not matches:
        st.error(
            "No matching stock was found. Try a company name (e.g. אלביט מערכות), "
            "a Hebrew symbol (e.g. אלבמע), or an English symbol (e.g. ESLT)."
        )
        return None, "", False

    picked = pick_security_match(stock_query, matches)
    if picked is not None:
        return picked.security_id, picked.display_label, True

    st.session_state.disambiguation_query = stock_query
    st.rerun()

    return None, "", False


def render_sidebar(*, show_dashboard_actions: bool) -> SidebarAction:
    with st.sidebar:
        _inject_sidebar_styles()
        analyze_clicked = False
        reload_clicked = False
        back_clicked = False
        stock_id: int | None = None
        stock_query = st.session_state.get("stock_query", DEFAULT_STOCK_QUERY)
        stock_label = st.session_state.get("stock_label", "")

        if show_dashboard_actions:
            st.markdown("**Current analysis**")
            st.text(st.session_state.get("stock_label", f"Security {st.session_state.stock_id}"))

            reload_clicked = st.button("Reload data", use_container_width=True)
            back_clicked = st.button("← Start over", use_container_width=True)

            st.divider()
            benchmark_id, risk_free_rate_annual = _render_advanced_settings()
            stock_id = int(st.session_state.stock_id)
        else:
            st.header("Portfolio Setup")
            st.caption("Markowitz + CAPM · 3-year lookback")

            stock_query = st.text_input(
                "Stock name or symbol",
                value=st.session_state.get("stock_query", DEFAULT_STOCK_QUERY),
                placeholder="e.g. ESLT, אלבמע, אלביט מערכות",
                help="Search by English or Hebrew company name, or ticker symbol.",
            )
            st.markdown(
                '<p class="sidebar-muted-hint">'
                "Examples: ESLT, אלבמע, אלביט מערכות, Teva, טבע"
                "</p>",
                unsafe_allow_html=True,
            )

            if st.button("Analyze this stock →", type="primary", use_container_width=True):
                stock_id, stock_label, analyze_clicked = _resolve_stock_selection(stock_query)

            st.markdown(
                '<p class="sidebar-load-hint">'
                "⏳ First load takes 30–60 seconds to fetch 3 years of data. "
                "A progress bar will appear on the next screen."
                "</p>",
                unsafe_allow_html=True,
            )

            st.markdown('<div class="sidebar-section-gap"></div>', unsafe_allow_html=True)
            st.divider()
            benchmark_id, risk_free_rate_annual = _render_advanced_settings()

    return SidebarAction(
        stock_id=stock_id,
        stock_query=stock_query,
        stock_label=stock_label,
        benchmark_id=benchmark_id,
        risk_free_rate_annual=risk_free_rate_annual,
        analyze_clicked=analyze_clicked,
        reload_clicked=reload_clicked,
        back_clicked=back_clicked,
    )
