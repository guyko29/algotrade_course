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
- **Expected-return forecast** — Historical vs CAPM vs ML side-by-side
- **Optimal allocation** — Markowitz weights that maximize the Sharpe ratio

## Financial logic

| Model | Role |
|-------|------|
| **Markowitz (1952)** | Finds the efficient mix of stock, index, and cash that offers the best risk-adjusted return |
| **CAPM** | Measures how sensitive the stock is to the broader market (beta) and whether it earns excess return (alpha) |
| **Historical VaR** | Estimates downside loss from real price history |
| **STL + GARCH** | Separates trend/seasonality and models future volatility for price bands |
| **ML return forecast** | Scikit-Learn / XGBoost predict the stock's forward drift from technical features |

### Bridging financial theory and machine learning

Classical portfolio theory needs one famously hard input: the **expected return (μ)**. Markowitz and CAPM are only as good as that estimate, yet the textbook default — the historical sample mean — is a noisy, backward-looking guess. This app keeps the theory as the decision framework but upgrades the *drift* assumption: a supervised model (XGBoost, with a Ridge baseline for interpretability) is trained on technical features (lagged returns, momentum, RSI, MACD, realized volatility) using **walk-forward, leakage-free validation** to forecast the stock's next-month return. That forecast is **shrunk toward the historical mean and clipped** for stability, then fed in as μ to the Markowitz optimizer — while the covariance matrix and GARCH volatility bands continue to model risk. The dashboard shows **Historical vs CAPM vs ML** expected returns side-by-side, so you can see exactly how a data-driven μ shifts the optimal allocation. The result is a concrete bridge between data-science tooling and financial theory rather than two disconnected exercises.

## Who is it for?

Students, analysts, and curious investors who want a **clear, visual explanation** of portfolio theory applied to a real TASE stock — not trading advice.

## Quick start

See **[SETUP_LOCAL.md](SETUP_LOCAL.md)** for installation, environment setup, and how to run the app.

## Disclaimer

This tool is for **education and research only**. It is not investment advice. Market data comes from public TASE endpoints and may change without notice. Forecasts rely on simplified statistical models.
