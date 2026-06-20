"""
TASE Scraper - תל-גוב צמודות 2-5 (Index 646)
מוריד נתוני EOD היסטוריים דרך HTTP ישיר ושומר ל-CSV + JSON
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import requests

ProgressCb = Callable[[str, Optional[float]], None]

DATA_DIR = Path(__file__).parent / "data"

DEFAULT_INDEX_ID = 646

FROM_DATE = "01/01/2020"
TO_DATE = datetime.today().strftime("%d/%m/%Y")

_API_URL = "https://api.tase.co.il/api/index/historyeod"
_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Origin": "https://market.tase.co.il",
    "Referer": "https://market.tase.co.il/",
}


def _to_api_date(dd_mm_yyyy: str) -> str:
    d, m, y = dd_mm_yyyy.split("/")
    return f"{y}-{m}-{d}"


def _fetch_page(from_date: str, to_date: str, index_id: int, page_num: int) -> dict:
    payload = {
        "pType": "8",
        "dFrom": from_date,
        "dTo": to_date,
        "TotalRec": 0,
        "oId": str(index_id),
        "lang": "0",
        "pageNum": page_num,
    }
    resp = requests.post(_API_URL, json=payload, headers=_HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.json()


def fetch_tase_data(
    from_date: str = FROM_DATE,
    to_date: str = TO_DATE,
    index_id: int = DEFAULT_INDEX_ID,
    progress_cb: Optional[ProgressCb] = None,
) -> list:
    def report(msg: str, frac: Optional[float] = None):
        print(msg)
        if progress_cb:
            progress_cb(msg, frac)

    api_from = _to_api_date(from_date)
    api_to = _to_api_date(to_date)

    items: list = []
    page_num = 1

    while True:
        report(f"📦 Fetching page {page_num}...", None)
        data = _fetch_page(api_from, api_to, index_id, page_num)
        batch = data.get("Items", [])
        if not batch:
            break
        items.extend(batch)
        report(f"📦 Page {page_num} — {len(batch)} items ({len(items)} total)", None)
        page_num += 1

    print(f"\n✅ Total records fetched: {len(items)}")
    if not items:
        print("⚠️  No data returned — check the date range or index ID")
    return items


def save_items(items: list, index_id: int) -> tuple[Path, Path]:
    DATA_DIR.mkdir(exist_ok=True)
    json_path = DATA_DIR / f"tase_{index_id}_data.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    csv_path = DATA_DIR / f"tase_{index_id}_data.csv"
    fieldnames = list(items[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(items)
    return json_path, csv_path


if __name__ == "__main__":
    items = fetch_tase_data()
    if items:
        json_path, csv_path = save_items(items, DEFAULT_INDEX_ID)
        print(f"💾 JSON saved to {json_path}")
        print(f"💾 CSV saved to {csv_path} ({len(items)} rows)")
