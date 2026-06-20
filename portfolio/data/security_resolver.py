"""Resolve TASE stock names and symbols to security IDs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

import requests

from portfolio.config import get_settings
from portfolio.errors import DataFetchError
from portfolio.logger import get_logger

logger = get_logger(__name__)

SEARCH_ENTITIES_URL = "https://api.tase.co.il/api/content/searchentities"
SHARE_TYPE = 1
SHARE_SUBTYPE = "1"


@dataclass(frozen=True)
class SecurityRecord:
    security_id: int
    name_en: str
    name_he: str
    symbol_en: str | None
    symbol_he: str | None

    @property
    def display_label(self) -> str:
        name = self.name_en or self.name_he or f"Security {self.security_id}"
        symbols: list[str] = []
        if self.symbol_en:
            symbols.append(self.symbol_en)
        if self.symbol_he and self.symbol_he not in symbols:
            symbols.append(self.symbol_he)
        if symbols:
            return f"{name} ({' / '.join(symbols)})"
        return name


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _normalize_key(value: str) -> str:
    return _normalize_text(value).casefold()


@lru_cache(maxsize=1)
def load_share_catalog() -> tuple[SecurityRecord, ...]:
    settings = get_settings()
    headers = {
        "Accept": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Origin": "https://market.tase.co.il",
        "Referer": "https://market.tase.co.il/",
    }

    merged: dict[int, dict[str, str | None]] = {}

    for lang_code, lang_key in ((0, "he"), (1, "en")):
        try:
            response = requests.get(
                SEARCH_ENTITIES_URL,
                params={"lang": lang_code},
                headers=headers,
                timeout=settings.tase_request_timeout_seconds,
            )
            response.raise_for_status()
            entities = response.json()
        except requests.RequestException as exc:
            logger.error("Failed loading TASE security catalog (lang=%s): %s", lang_code, exc)
            raise DataFetchError(str(exc)) from exc

        if not isinstance(entities, list):
            continue

        for entity in entities:
            if entity.get("Type") != SHARE_TYPE or str(entity.get("SubType")) != SHARE_SUBTYPE:
                continue
            try:
                security_id = int(entity["Id"])
            except (KeyError, TypeError, ValueError):
                continue

            entry = merged.setdefault(
                security_id,
                {"name_en": "", "name_he": "", "symbol_en": None, "symbol_he": None},
            )
            name = _normalize_text(str(entity.get("Name") or ""))
            symbol = entity.get("Smb")
            symbol = _normalize_text(str(symbol)) if symbol else None

            if lang_key == "en":
                if name:
                    entry["name_en"] = name
                if symbol:
                    entry["symbol_en"] = symbol
            else:
                if name:
                    entry["name_he"] = name
                if symbol:
                    entry["symbol_he"] = symbol

    catalog = tuple(
        SecurityRecord(
            security_id=security_id,
            name_en=str(values["name_en"] or values["name_he"]),
            name_he=str(values["name_he"] or values["name_en"]),
            symbol_en=values["symbol_en"],
            symbol_he=values["symbol_he"],
        )
        for security_id, values in merged.items()
    )
    logger.info("Loaded %s tradable share records for lookup", len(catalog))
    return catalog


def _iter_search_fields(record: SecurityRecord) -> Iterable[str]:
    for value in (record.name_en, record.name_he, record.symbol_en, record.symbol_he):
        if value:
            yield value


def _score_match(query_key: str, field: str) -> int:
    field_key = _normalize_key(field)
    if query_key == field_key:
        return 100
    if field_key.startswith(query_key):
        return 80
    if query_key in field_key:
        return 60
    return 0


def search_securities(query: str, *, limit: int = 8) -> list[SecurityRecord]:
    query = _normalize_text(query)
    if not query:
        return []

    if query.isdigit():
        security_id = int(query)
        for record in load_share_catalog():
            if record.security_id == security_id:
                return [record]
        return []

    query_key = _normalize_key(query)
    scored: list[tuple[int, SecurityRecord]] = []

    for record in load_share_catalog():
        best = 0
        for field in _iter_search_fields(record):
            best = max(best, _score_match(query_key, field))
            if best == 100:
                break
        if best > 0:
            scored.append((best, record))

    scored.sort(key=lambda item: (-item[0], item[1].display_label))
    return [record for _, record in scored[:limit]]


def pick_security_match(query: str, matches: list[SecurityRecord]) -> SecurityRecord | None:
    """Return a single unambiguous match, or None when the user must choose."""
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]

    query_key = _normalize_key(query)
    exact = [
        record
        for record in matches
        if any(_normalize_key(field) == query_key for field in _iter_search_fields(record))
    ]
    if len(exact) == 1:
        return exact[0]
    return None


def get_security_record(security_id: int) -> SecurityRecord | None:
    for record in load_share_catalog():
        if record.security_id == security_id:
            return record
    return None
