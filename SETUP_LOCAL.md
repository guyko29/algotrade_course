# Local Setup Guide

Technical instructions for running the TASE Optimal Portfolio Analyzer on your machine.

## Prerequisites

- **Python 3.10+** (3.12 recommended)
- **Internet access** (live TASE API calls)
- **Git** (optional)

## 1. Clone and enter the project

```bash
git clone <your-repo-url>
cd algotrade_course
```

## 2. Create a virtual environment

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure environment variables

Copy the template and create your local `.env` file:

**Windows:**

```powershell
copy .env.template .env
```

**macOS / Linux:**

```bash
cp .env.template .env
```

### Key variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`) |
| `LOG_FILE` | `logs/app.log` | Rotating log file path |
| `TASE_API_KEY` | *(empty)* | Optional — only needed if you switch to the official TASE DataHub API |
| `TASE_INDEX_API_URL` | public index endpoint | Override only if TASE changes URLs |
| `TASE_SECURITY_API_URL` | public security endpoint | Override only if TASE changes URLs |
| `DEFAULT_BENCHMARK` | `TA35` | Default market benchmark (`TA35` or `TA125`) |
| `DEFAULT_RISK_FREE_RATE_ANNUAL` | `0.045` | 4.5% annual risk-free rate |
| `LOOKBACK_YEARS` | `3` | Historical data window |
| `MIN_OVERLAPPING_TRADING_DAYS` | `60` | Minimum days required for analysis |

You do **not** need an API key for the current public endpoints.

## 5. Run the app

```bash
python -m streamlit run app.py
```

Open **http://localhost:8501** in your browser.

## 6. Using the app

1. On the home screen, enter a **TASE security number**
2. Click **Analyze this stock →**
3. Wait 30–60 seconds while data loads (progress bar appears)
4. Explore the English ECharts dashboard

Optional settings (benchmark, risk-free rate) are in the sidebar under **Advanced settings**.

### Finding a security ID

1. Go to [market.tase.co.il](https://market.tase.co.il)
2. Open a stock page
3. Use the numeric ID from the URL or security details

## Project structure

```
algotrade_course/
├── app.py                      # Streamlit entrypoint (thin)
├── portfolio/
│   ├── config.py               # Settings from .env
│   ├── logger.py               # Centralized logging
│   ├── errors.py               # Domain errors + UI handling
│   ├── constants.py            # Market IDs and labels
│   ├── data/
│   │   └── tase_client.py      # TASE HTTP client
│   ├── analytics/
│   │   ├── portfolio_service.py  # Orchestrates full analysis
│   │   ├── capm.py             # CAPM calculations
│   │   ├── markowitz.py        # Sharpe optimization
│   │   ├── risk_metrics.py     # VaR, distributions, rolling vol
│   │   └── forecast.py         # STL + GARCH forecast
│   ├── charts/
│   │   └── echarts.py          # Apache ECharts rendering
│   └── ui/
│       ├── landing_page.py     # Simple stock input screen
│       ├── dashboard_page.py   # Results dashboard
│       └── sidebar.py          # Advanced settings
├── logs/                       # Auto-created at runtime
├── .env.template
└── requirements.txt
```

## Logs

Runtime logs are written to `logs/app.log` (configurable via `LOG_FILE`). Check this file when debugging data-fetch or chart issues.

## Deployment (Railway)

The included `railway.toml` starts:

```bash
streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
```

Set environment variables in the Railway dashboard using the same keys from `.env.template`.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Charts not showing | Hard-refresh the browser (`Ctrl+Shift+R`) |
| "No price history" error | Verify the security ID on market.tase.co.il |
| TA-125 empty data | Expected — app auto-falls back to TA-35 |
| Slow first load | Normal — ~25 API pages × 2 instruments |
| `streamlit` not found | Use `python -m streamlit run app.py` |

## Disclaimer

For local development and academic use only. Not investment advice.
