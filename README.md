# algotraid

Small toolkit for **Tel Aviv Stock Exchange (TASE)** index data: a Streamlit dashboard with risk-style metrics and a Monte Carlo price forecast, plus a historical notebook.

## What’s included

- **`app.py`** — Streamlit UI (Hebrew labels). Pick an index or enter an index ID, date range, then load data. Shows annualized volatility, period return, historical 5% daily and annual downside (VaR-style), price chart, GBM-based Monte Carlo forecast (median and 5th–95th percentiles), raw table, and CSV download.
- **`scraper.py`** — Fetches end-of-day index history from the public TASE API (`api.tase.co.il`).
- **`analytics.py`** — Pure functions: price series, metrics, Monte Carlo simulation (no Streamlit dependency).
- **`Robo_Adviser_Prod_20240529.ipynb`** — Standalone Jupyter analysis (run separately from the app).

## Requirements

- **Python 3.10+** (3.13 works with the pinned versions in `requirements.txt`).
- **Network access** when using the dashboard or scraper (live API calls).

## Setup

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run the dashboard

```bash
streamlit run app.py
```

Open the URL shown in the terminal (typically `http://localhost:8501`). Use the sidebar to choose an index, set dates, and click **טען נתונים**.

## Run the notebook

```bash
pip install jupyter ipykernel
jupyter notebook Robo_Adviser_Prod_20240529.ipynb
```

## Project layout

| Path | Role |
|------|------|
| `app.py` | Streamlit entrypoint |
| `analytics.py` | Metrics and Monte Carlo |
| `scraper.py` | TASE HTTP client |
| `requirements.txt` | `streamlit`, `requests` (pandas/numpy come via Streamlit) |
| `data/` | Used by the scraper for local artifacts when saving |

## Disclaimer

This project is for **education and exploration only**. It is not investment advice. The TASE API may change or rate-limit; forecasts rely on simplified assumptions (e.g. GBM) and historical statistics.
