"""
WB-PREPARE-COUNTRIES-ONLY v2026.01.31-03

Reliable enrichment for a World Bank indicator tidy CSV by querying
/country/{iso3} for each distinct country_iso3 in the file.

Input:
  data/worldbank_NE.CON.GOVT.ZS.csv

Output:
  data/worldbank_NE.CON.GOVT.ZS_countries_only.csv

Rules:
- If /country/{iso3} returns iso2Code == "" -> treat as aggregate and drop.
- Adds: region, income_level, lending_type
"""

from __future__ import annotations

import csv
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import requests

WB_API = "https://api.worldbank.org/v2"


@dataclass(frozen=True)
class Meta:
    iso3: str
    iso2: str
    name: str
    region: str
    income_level: str
    lending_type: str


def _get_json(url: str, params: Dict[str, Any], timeout: int = 30) -> Any:
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def fetch_meta_by_iso3(iso3: str) -> Optional[Meta]:
    """
    Endpoint:
      /country/{code}?format=json
    World Bank accepts iso3 codes for many calls.
    Returns None if not found / unexpected.
    """
    url = f"{WB_API}/country/{iso3}"
    try:
        data = _get_json(url, params={"format": "json"}, timeout=30)
    except Exception:
        return None

    # Expected: [meta, [country_obj]]
    if not isinstance(data, list) or len(data) < 2 or not data[1]:
        return None

    it = data[1][0]  # first match
    iso2 = (it.get("iso2Code") or "").strip()
    name = (it.get("name") or "").strip()
    region = ((it.get("region") or {}).get("value") or "").strip()
    income = ((it.get("incomeLevel") or {}).get("value") or "").strip()
    lending = ((it.get("lendingType") or {}).get("value") or "").strip()

    return Meta(
        iso3=iso3,
        iso2=iso2,
        name=name,
        region=region,
        income_level=income,
        lending_type=lending,
    )


def main() -> int:
    inp = "data/worldbank_NE.CON.GOVT.ZS.csv"
    outp = "data/worldbank_NE.CON.GOVT.ZS_countries_only.csv"

    if not os.path.exists(inp):
        print(f"ERROR: input not found: {inp}", file=sys.stderr)
        return 2

    # Read input rows and collect unique iso3 codes
    raw_rows: List[Dict[str, str]] = []
    iso3_set: Set[str] = set()

    with open(inp, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            raw_rows.append(row)
            iso3 = (row.get("country_iso3") or "").strip()
            if iso3:
                iso3_set.add(iso3)

    # Fetch metadata per iso3 (with memoization)
    meta_map: Dict[str, Meta] = {}
    missing_meta = 0
    aggregates = 0

    for iso3 in sorted(iso3_set):
        m = fetch_meta_by_iso3(iso3)
        if m is None:
            missing_meta += 1
            continue
        if m.iso2 == "":
            aggregates += 1
            continue
        meta_map[iso3] = m

    kept: List[Dict[str, str]] = []
    for row in raw_rows:
        iso3 = (row.get("country_iso3") or "").strip()
        if iso3 not in meta_map:
            continue
        m = meta_map[iso3]
        kept.append(
            {
                "country_name": row.get("country_name", ""),
                "country_iso3": iso3,
                "region": m.region,
                "income_level": m.income_level,
                "lending_type": m.lending_type,
                "year": row.get("year", ""),
                "value": row.get("value", ""),
            }
        )

    os.makedirs("data", exist_ok=True)
    with open(outp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "country_name",
                "country_iso3",
                "region",
                "income_level",
                "lending_type",
                "year",
                "value",
            ],
        )
        w.writeheader()
        for r in kept:
            w.writerow(r)

    print(f"OK: saved {len(kept)} rows -> {outp}")
    print(f"Meta: countries={len(meta_map)} aggregates_dropped={aggregates} missing_meta={missing_meta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
