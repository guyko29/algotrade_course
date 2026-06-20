"""Domain-specific exceptions and UI-friendly error handling."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import streamlit as st


class PortfolioError(Exception):
    """Base exception for portfolio analysis failures."""

    user_message: str = "Something went wrong. Please try again."

    def __init__(self, message: str, *, user_message: str | None = None):
        super().__init__(message)
        if user_message:
            self.user_message = user_message


class DataFetchError(PortfolioError):
    user_message = "Could not reach the TASE market data service. Check your connection and try again."


class InvalidSecurityError(PortfolioError):
    user_message = "No price history was found for this security ID. Verify the number on market.tase.co.il."


class SecurityNotFoundError(PortfolioError):
    user_message = "No matching stock was found. Try a company name or ticker symbol."


class BenchmarkDataError(PortfolioError):
    user_message = "Could not load benchmark index data. Try again or switch the benchmark."


class InsufficientDataError(PortfolioError):
    user_message = "Not enough overlapping trading days between the stock and the benchmark."


class ChartRenderError(PortfolioError):
    user_message = "A chart could not be rendered. Other results are still valid."


def display_error(ui: st, error: Exception) -> None:
    """Show a user-friendly message and log the underlying exception."""
    from portfolio.logger import get_logger

    logger = get_logger(__name__)

    if isinstance(error, PortfolioError):
        logger.warning("%s: %s", type(error).__name__, error)
        ui.error(error.user_message)
        return

    logger.exception("Unexpected error: %s", error)
    ui.error("An unexpected error occurred. Please try again or contact support.")
