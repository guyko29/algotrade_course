"""Landing page — centered hero placeholder until analysis runs."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

LOGO_PATH = Path(__file__).resolve().parents[2] / "assets" / "logo.png"


def render_landing_page() -> None:
    """Render the welcome screen in the main content area."""
    st.markdown(
        """
        <style>
        .landing-hero {
            text-align: center;
            padding: 3rem 2rem 2rem;
        }
        .landing-title {
            font-size: 2rem;
            font-weight: 700;
            color: #1a1a2e;
            margin: 1.25rem 0 0.35rem 0;
            letter-spacing: -0.02em;
        }
        .landing-tagline {
            font-size: 1.25rem;
            font-weight: 500;
            color: #0f3460;
            margin: 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    _, center, _ = st.columns([1, 2, 1])
    with center:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), use_container_width=True)
        else:
            st.warning("Logo image not found in assets/logo.png")

    st.markdown(
        """
        <div class="landing-hero">
            <p class="landing-title">From Data Mining to AlgoTrade</p>
            <p class="landing-tagline">Portfolio Analyzer</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
