"""HTTP client for TASE end-of-day price history."""

from __future__ import annotations

from datetime import date
from typing import Callable, Optional

import requests

from portfolio.config import get_settings
from portfolio.constants import TA125_INDEX_ID, TA35_INDEX_ID
from portfolio.errors import BenchmarkDataError, DataFetchError, InvalidSecurityError
from portfolio.logger import get_logger

ProgressCallback = Callable[[str, Optional[float]], None]
logger = get_logger(__name__)


class TaseClient:
    """Fetches historical EOD rows for TASE securities and indices."""

    def __init__(self) -> None:
        settings = get_settings()
        self._index_url = settings.tase_index_api_url
        self._security_url = settings.tase_security_api_url
        self._timeout = settings.tase_request_timeout_seconds
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Origin": "https://market.tase.co.il",
            "Referer": "https://market.tase.co.il/",
        }
        if settings.tase_api_key:
            self._headers["apikey"] = settings.tase_api_key

    @staticmethod
    def _to_api_date(value: date | str) -> str:
        if isinstance(value, date):
            return value.strftime("%Y-%m-%d")
        if "/" in value:
            day, month, year = value.split("/")
            return f"{year}-{month}-{day}"
        return value

    def _fetch_pages(
        self,
        url: str,
        object_id: int | str,
        from_date: date,
        to_date: date,
        progress_cb: ProgressCallback | None = None,
        label: str = "data",
    ) -> list[dict]:
        api_from = self._to_api_date(from_date)
        api_to = self._to_api_date(to_date)
        items: list[dict] = []
        page_num = 1

        logger.info("Fetching %s for object_id=%s (%s to %s)", label, object_id, api_from, api_to)

        while True:
            if progress_cb:
                progress_cb(f"Fetching page {page_num}...", min(page_num / 30.0, 0.95))

            payload = {
                "pType": "8",
                "dFrom": api_from,
                "dTo": api_to,
                "TotalRec": 0,
                "oId": str(object_id),
                "lang": "0",
                "pageNum": page_num,
            }
            try:
                response = requests.post(
                    url,
                    json=payload,
                    headers=self._headers,
                    timeout=self._timeout,
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                logger.error("TASE request failed on page %s: %s", page_num, exc)
                raise DataFetchError(str(exc)) from exc

            batch = response.json().get("Items", [])
            if not batch:
                break

            items.extend(batch)
            logger.debug("Page %s returned %s rows (%s total)", page_num, len(batch), len(items))
            if progress_cb:
                progress_cb(
                    f"Page {page_num}: {len(batch)} rows ({len(items)} total)",
                    min(page_num / 30.0, 0.95),
                )
            page_num += 1

        logger.info("Fetched %s rows for object_id=%s", len(items), object_id)
        return items

    def fetch_security_history(
        self,
        security_id: int | str,
        from_date: date,
        to_date: date,
        progress_cb: ProgressCallback | None = None,
    ) -> list[dict]:
        items = self._fetch_pages(
            self._security_url,
            security_id,
            from_date,
            to_date,
            progress_cb,
            label="security",
        )
        if not items:
            raise InvalidSecurityError(f"No rows for security_id={security_id}")
        return items

    def fetch_index_history(
        self,
        index_id: int,
        from_date: date,
        to_date: date,
        progress_cb: ProgressCallback | None = None,
    ) -> list[dict]:
        items = self._fetch_pages(
            self._index_url,
            index_id,
            from_date,
            to_date,
            progress_cb,
            label="index",
        )
        if not items:
            raise BenchmarkDataError(f"No rows for index_id={index_id}")
        return items

    def fetch_benchmark_with_fallback(
        self,
        benchmark_id: int,
        from_date: date,
        to_date: date,
        progress_cb: ProgressCallback | None = None,
    ) -> tuple[list[dict], int]:
        """Return benchmark rows and the index ID actually used."""
        try:
            return self.fetch_index_history(benchmark_id, from_date, to_date, progress_cb), benchmark_id
        except BenchmarkDataError:
            if benchmark_id == TA35_INDEX_ID:
                raise
            logger.warning("Benchmark %s unavailable; falling back to TA-35", benchmark_id)
            return (
                self.fetch_index_history(TA35_INDEX_ID, from_date, to_date, progress_cb),
                TA35_INDEX_ID,
            )
