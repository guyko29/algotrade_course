# TASE Optimal Portfolio Analyzer

An educational dashboard that helps you understand how a specific Israeli stock fits into a simple, optimal portfolio.

## What it does

Enter a **TASE security number** and the app builds a three-asset portfolio:

**Your stock · Market index (TA-35) · Risk-free cash**

It then shows:

- **Risk profile** — volatility, beta, and correlations
- **Return distribution** — how daily returns behave vs. a normal curve
- **Downside scenarios** — worst-case loss estimates (5th percentile)
- **Price forecast** — STL trend + GARCH volatility bands
- **Optimal allocation** — Markowitz weights that maximize the Sharpe ratio

## Financial logic

| Model | Role |
|-------|------|
| **Markowitz (1952)** | Finds the efficient mix of stock, index, and cash that offers the best risk-adjusted return |
| **CAPM** | Measures how sensitive the stock is to the broader market (beta) and whether it earns excess return (alpha) |
| **Historical VaR** | Estimates downside loss from real price history |
| **STL + GARCH** | Separates trend/seasonality and models future volatility for price bands |

## Who is it for?

Students, analysts, and curious investors who want a **clear, visual explanation** of portfolio theory applied to a real TASE stock — not trading advice.

## Quick start

See **[SETUP_LOCAL.md](SETUP_LOCAL.md)** for installation, environment setup, and how to run the app.

## Disclaimer

This tool is for **education and research only**. It is not investment advice. Market data comes from public TASE endpoints and may change without notice. Forecasts rely on simplified statistical models.
