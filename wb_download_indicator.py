"""
WB-DOWNLOAD-INDICATOR v2026.01.31-01

Downloads a World Bank indicator via the official API and saves a tidy CSV.

Default indicator:
- NE.CON.GOVT.ZS  (General government final consumption expenditure, % of GDP)

Output CSV columns:
- country_name
- country_iso3
- year
- value

Usage (PowerShell):
  python .\scripts\wb_download_indicator.py --indicator NE.CON.GOVT.ZS

Notes:
- No secrets needed.
- If you hit network issues, just rerun (idempotent overwrite by default).
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests


WB_API = "https://api.worldbank.org/v2"


@dataclass(frozen=True)
class Row:
    country_name: str
    country_iso3: str
    year: int
    value: Optional[float]


def _get_json(url: str, params: Dict[str, Any], timeout: int = 30) -> Any:
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def fetch_indicator_all_countries(indicator: str, per_page: int = 20000) -> List[Row]:
    """
    World Bank API endpoint:
      /country/all/indicator/{indicator}?format=json
    Returns:
      list of Row
    """
    url = f"{WB_API}/country/all/indicator/{indicator}"

    # First request: get paging info
    params = {"format": "json", "per_page": per_page, "page": 1}
    data = _get_json(url, params=params)

    if not isinstance(data, list) or len(data) < 2:
        raise RuntimeError(f"Unexpected API response shape for indicator={indicator}: {type(data)}")

    meta = data[0] or {}
    total_pages = int(meta.get("pages") or 1)

    rows: List[Row] = []
    for page in range(1, total_pages + 1):
        params["page"] = page
        page_data = _get_json(url, params=params)

        # page_data[1] is the actual list
        items = page_data[1]
        if not items:
            continue

        for it in items:
            # Some records may be partially missing
            country = it.get("country") or {}
            iso3 = (it.get("countryiso3code") or "").strip()
            date_str = (it.get("date") or "").strip()
            val = it.get("value", None)

            if not date_str.isdigit():
                continue
            year = int(date_str)

            value_f: Optional[float]
            if val is None:
                value_f = None
            else:
                try:
                    value_f = float(val)
                except Exception:
                    value_f = None

            rows.append(
                Row(
                    country_name=str(country.get("value") or "").strip(),
                    country_iso3=iso3,
                    year=year,
                    value=value_f,
                )
            )

    # Basic cleanup: drop empty country names / iso3
    rows = [r for r in rows if r.country_name and r.country_iso3 and r.year]
    return rows


def write_csv(rows: List[Row], out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["country_name", "country_iso3", "year", "value"])
        for r in rows:
            w.writerow([r.country_name, r.country_iso3, r.year, "" if r.value is None else r.value])


def build_cli() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Download World Bank indicator data to tidy CSV.")
    p.add_argument("--indicator", default="NE.CON.GOVT.ZS", help="World Bank indicator code")
    p.add_argument("--out", default="", help="Output CSV path. Default: data/worldbank_<indicator>.csv")
    return p


def main() -> int:
    args = build_cli().parse_args()
    indicator = args.indicator.strip()
    out_path = args.out.strip() or os.path.join("data", f"worldbank_{indicator}.csv")

    try:
        rows = fetch_indicator_all_countries(indicator=indicator)
        if not rows:
            print(f"No rows returned for indicator={indicator}", file=sys.stderr)
            return 2
        write_csv(rows, out_path)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    # Minimal run summary
    years = [r.year for r in rows]
    print(f"OK: saved {len(rows)} rows -> {out_path}")
    print(f"Years: {min(years)}..{max(years)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
