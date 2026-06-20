"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    app_env: str
    log_level: str
    log_file: Path
    tase_api_key: str | None
    tase_index_api_url: str
    tase_security_api_url: str
    tase_request_timeout_seconds: int
    default_benchmark: str
    default_risk_free_rate_annual: float
    lookback_years: int
    min_overlapping_trading_days: int


@lru_cache
def get_settings() -> Settings:
    log_file = PROJECT_ROOT / os.getenv("LOG_FILE", "logs/app.log")
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        log_file=log_file,
        tase_api_key=os.getenv("TASE_API_KEY") or None,
        tase_index_api_url=os.getenv(
            "TASE_INDEX_API_URL",
            "https://api.tase.co.il/api/index/historyeod",
        ),
        tase_security_api_url=os.getenv(
            "TASE_SECURITY_API_URL",
            "https://api.tase.co.il/api/security/historyeod",
        ),
        tase_request_timeout_seconds=int(os.getenv("TASE_REQUEST_TIMEOUT_SECONDS", "20")),
        default_benchmark=os.getenv("DEFAULT_BENCHMARK", "TA35").upper(),
        default_risk_free_rate_annual=float(os.getenv("DEFAULT_RISK_FREE_RATE_ANNUAL", "0.045")),
        lookback_years=int(os.getenv("LOOKBACK_YEARS", "3")),
        min_overlapping_trading_days=int(os.getenv("MIN_OVERLAPPING_TRADING_DAYS", "60")),
    )
