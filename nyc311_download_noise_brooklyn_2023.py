"""
NYC311-DOWNLOAD-NOISE-BROOKLYN-2023 v2026.01.31-01

Downloads NYC 311 slice via Socrata SODA2 (no auth required):
- complaint_type = "Noise - Residential"
- borough = "BROOKLYN"
- created_date in 2023
Saves to CSV.

Notes:
- SODA2 default limit is 1000 unless you set $limit; max practical per request often 50000.
- Uses pagination with $offset.
- Optional: set env var SOCRATA_APP_TOKEN to be polite / avoid throttling.
"""

from __future__ import annotations

import csv
import os
import sys
import time
from typing import Dict, List, Optional

import requests

BASE_URL = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"

SELECT_COLUMNS = [
    "unique_key",
    "created_date",
    "closed_date",
    "complaint_type",
    "descriptor",
    "location_type",
    "incident_address",
    "street_name",
    "incident_zip",
    "borough",
    "city",
    "latitude",
    "longitude",
    "agency",
    "status",
    "resolution_description",
]

WHERE_CLAUSE = (
    "complaint_type='Noise - Residential' "
    "AND borough='BROOKLYN' "
    "AND created_date between '2023-01-01T00:00:00' and '2023-12-31T23:59:59'"
)

OUT_PATH = os.path.join("data", "nyc311_noise_residential_brooklyn_2023.csv")


def fetch_page(limit: int, offset: int, session: requests.Session) -> List[Dict[str, str]]:
    params = {
        "$select": ",".join(SELECT_COLUMNS),
        "$where": WHERE_CLAUSE,
        "$limit": str(limit),
        "$offset": str(offset),
        "$order": "created_date ASC",
    }

    headers = {}
    app_token = os.getenv("SOCRATA_APP_TOKEN", "").strip()
    if app_token:
        headers["X-App-Token"] = app_token

    r = session.get(BASE_URL, params=params, headers=headers, timeout=60)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected response type: {type(data)}")
    # Ensure strings
    out: List[Dict[str, str]] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        out.append({k: ("" if row.get(k) is None else str(row.get(k))) for k in SELECT_COLUMNS})
    return out


def write_csv(rows: List[Dict[str, str]], path: str, write_header: bool) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mode = "w" if write_header else "a"
    with open(path, mode, newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SELECT_COLUMNS)
        if write_header:
            w.writeheader()
        for r in rows:
            w.writerow(r)


def main() -> int:
    page_limit = 50000  # good practical chunk
    max_rows = 250000   # safety cap for portfolio slice (can raise later)

    total = 0
    offset = 0
    started = time.time()

    # Start fresh each run
    if os.path.exists(OUT_PATH):
        os.remove(OUT_PATH)

    with requests.Session() as s:
        while True:
            # simple retry loop
            for attempt in range(1, 4):
                try:
                    rows = fetch_page(limit=page_limit, offset=offset, session=s)
                    break
                except Exception as e:
                    if attempt == 3:
                        print(f"ERROR: failed after retries at offset={offset}: {e}", file=sys.stderr)
                        return 1
                    time.sleep(2 * attempt)

            if not rows:
                break

            write_csv(rows, OUT_PATH, write_header=(total == 0))
            got = len(rows)
            total += got
            offset += got

            print(f"Fetched {got} rows (total={total})")

            if total >= max_rows:
                print(f"STOP: reached max_rows={max_rows} (increase in script if you want more).")
                break

            # be polite
            time.sleep(0.2)

    elapsed = time.time() - started
    print(f"OK: saved {total} rows -> {OUT_PATH}")
    print(f"Elapsed: {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
