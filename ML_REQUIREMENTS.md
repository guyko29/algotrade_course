# ML Requirements — Bridging Data Science and Financial Theory

This document defines the **machine-learning upgrade path** for the TASE Optimal Portfolio Analyzer. It is written to align with the course syllabus, which explicitly requires connecting **data-science tooling** with **financial theory** (Markowitz, CAPM, risk modeling).

---

## 1. Academic Gap in the Current System

The app already implements solid financial theory:

| Module | File | What it does today |
|--------|------|--------------------|
| CAPM | `portfolio/analytics/capm.py` | Beta, alpha, R², CAPM expected return |
| Markowitz | `portfolio/analytics/markowitz.py` | Max-Sharpe weights over [Stock, Index, Risk-Free] |
| Gaussian risk | `portfolio/analytics/risk_metrics.py` | Monthly return distribution & downside |
| Time-series forecast | `portfolio/analytics/forecast.py` | STL + GARCH price bands (visual only) |

However, the **expected-return inputs** for portfolio optimization still rely on **simple historical averages**:

```72:76:portfolio/analytics/markowitz.py
    expected_daily_returns = np.array([
        aligned["stock"].mean(),
        aligned["index"].mean(),
        risk_free_daily,
    ])
```

Similarly, Gaussian risk uses the **sample mean** of past returns (`portfolio/analytics/risk_metrics.py`, `calculate_monthly_gaussian_risk`), and CAPM expected return is derived from historical market premium (`portfolio/analytics/capm.py`).

From a grading perspective, this is a missed opportunity: the instructor expects to see **practical use of ML libraries taught in class** (e.g. **Scikit-Learn**, **XGBoost**), not only classical statistics.

---

## 2. Recommended Solution (Simple & High-Impact)

**Upgrade the return-forecasting layer** so that Markowitz and CAPM consume **ML-predicted expected returns** instead of naive historical means.

### Core idea

1. Build a feature matrix from past prices and technical indicators (RSI, moving averages, momentum, volatility, etc.).
2. Train a supervised regressor to predict **next-period log return** (or next-month return).
3. Use the model's **out-of-sample / walk-forward prediction** as the expected return for the stock (and optionally the index).
4. Feed those predictions into the Markowitz optimizer and compare them against CAPM-implied returns on the dashboard.

### Suggested models (pick one primary, one baseline)

| Model | Library | Role |
|-------|---------|------|
| `LinearRegression` or `Ridge` | Scikit-Learn | Interpretable baseline (links cleanly to CAPM intuition) |
| `XGBRegressor` | XGBoost | Strong non-linear benchmark expected by the syllabus |
| `RandomForestRegressor` | Scikit-Learn | Optional ensemble comparison |

Use **time-series-aware validation** (walk-forward or expanding window) — never shuffle rows randomly.

---

## 3. Where Each Piece Should Live in the Codebase

### 3.1 New files to create

```
portfolio/analytics/
├── features.py          # Technical indicators & feature engineering
├── ml_forecast.py       # Train/predict return models (sklearn + xgboost)
└── expected_returns.py  # Single entry point: historical vs ML vs CAPM returns
```

| File | Responsibility |
|------|----------------|
| `features.py` | Turn `stock_prices`, `index_prices` into a `pd.DataFrame` of lagged returns, rolling vol, SMA/EMA, RSI, MACD, etc. Target column: `next_log_return`. |
| `ml_forecast.py` | `train_return_model(features, model_type="xgboost")`, `predict_next_return(model, latest_features)`, walk-forward CV metrics (MAE, RMSE, R²). |
| `expected_returns.py` | `build_expected_returns(stock_returns, index_returns, stock_prices, index_prices, capm_result) -> ExpectedReturnsResult` — returns daily/annual expected returns for stock & index from ML, plus fallback to historical mean if training fails. |

### 3.2 Files to modify

| File | Change |
|------|--------|
| `portfolio/analytics/models.py` | Add dataclasses: `MlForecastResult`, `ExpectedReturnsResult` (predicted stock/index daily return, model name, CV score, feature importance). Extend `PortfolioAnalysis` with `ml_forecast` and `expected_returns` fields. |
| `portfolio/analytics/markowitz.py` | Change `optimize_max_sharpe_portfolio(...)` to accept optional `expected_daily_returns: np.ndarray \| None`. If provided, use ML/CAPM-informed vector instead of `aligned.mean()`. |
| `portfolio/analytics/capm.py` | Optional: add `expected_return_ml_adjusted` or document side-by-side comparison (CAPM theory vs ML forecast vs historical). |
| `portfolio/analytics/portfolio_service.py` | **Orchestration hub** — after line ~98 (`stock_returns`, `index_returns`), call feature engineering → ML training → `build_expected_returns()` → pass result into `optimize_max_sharpe_portfolio()`. |
| `portfolio/analytics/risk_metrics.py` | Optional upgrade: use ML-predicted monthly return as `expected_monthly_pct` in `calculate_monthly_gaussian_risk` instead of `returns.mean()`. |
| `portfolio/config.py` / `.env.template` | Add `ML_MODEL=xgboost`, `ML_HORIZON_DAYS=21`, `ML_MIN_TRAIN_ROWS=252`. |
| `portfolio/ui/dashboard_page.py` | New subsection under **Optimal Portfolio** or **Returns**: show model name, predicted vs historical expected return, CV metrics, feature importance chart. |
| `portfolio/charts/echarts.py` | Optional: `render_feature_importance_chart()`, `render_actual_vs_predicted_chart()`. |
| `requirements.txt` | Add `scikit-learn>=1.3.0,<2.0.0` and `xgboost>=2.0.0,<4.0.0`. |

### 3.3 Files that should **not** be replaced

| File | Keep as-is |
|------|------------|
| `portfolio/analytics/forecast.py` | STL + GARCH remains a **volatility / price-band** module (time-series econometrics). ML handles **expected return**; GARCH handles **uncertainty bands** — complementary, not redundant. |
| `portfolio/data/tase_client.py` | Data ingestion only — no ML logic here. |

---

## 4. Data Flow (Target Architecture)

```
TASE API (tase_client.py)
        │
        ▼
portfolio_service.py  ──►  prices & log returns
        │
        ├──► features.py  ──►  indicator DataFrame
        │         │
        │         ▼
        │    ml_forecast.py  ──►  trained model + next-return prediction
        │         │
        │         ▼
        ├──► expected_returns.py  ──►  μ_stock, μ_index (daily)
        │         │
        ├──► capm.py  ──►  β, α, CAPM E[R]  (theory benchmark)
        │         │
        ▼         ▼
   markowitz.py  ──►  optimal weights (uses ML μ vector)
        │
        ▼
   dashboard_page.py  ──►  compare Historical vs CAPM vs ML expected returns
```

---

## 5. Implementation Checklist

- [ ] Add `scikit-learn` and `xgboost` to `requirements.txt`
- [ ] Implement `features.py` with at least 5 technical indicators
- [ ] Implement walk-forward training in `ml_forecast.py` (no data leakage)
- [ ] Wire `expected_returns.py` into `portfolio_service.py` (lines 100–114)
- [ ] Pass ML expected returns into `optimize_max_sharpe_portfolio()` in `markowitz.py`
- [ ] Extend `PortfolioAnalysis` model and dashboard UI to display ML vs CAPM vs historical
- [ ] Log model metrics to `logs/app.log` via `portfolio/logger.py`
- [ ] Document the financial narrative in `README.md` (one paragraph: theory + ML bridge)

---

## 6. How This Satisfies the Syllabus

| Course expectation | How the upgrade addresses it |
|--------------------|------------------------------|
| Data-science tooling | Scikit-Learn / XGBoost training, CV, feature engineering |
| Financial theory | Markowitz optimization & CAPM remain the decision framework |
| Practical integration | ML output becomes **μ** in the optimizer — not a standalone notebook |
| Risk modeling | Gaussian / GARCH modules stay; ML improves the **drift** assumption |
| Interpretability | Linear baseline + feature importance + CAPM side-by-side comparison |

---

## 7. Minimal Viable Demo (for grading)

Even a **single-stock, single-horizon** implementation is enough if presented clearly:

1. Train `XGBRegressor` on 3 years of daily features.
2. Predict next-month log return for the selected TASE stock.
3. Show on the dashboard:
   - Historical mean annual return: **X%**
   - CAPM expected return: **Y%**
   - ML predicted return: **Z%**
   - Markowitz optimal weights using **Z%** (and how weights shift vs historical **X%**)

That single comparison demonstrates both **ML competence** and **financial literacy** — the exact bridge the syllabus asks for.
