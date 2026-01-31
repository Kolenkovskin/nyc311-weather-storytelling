"""
DATASET-SEARCH-MULTI v2026.01.31-02

Ищет датасеты в 3 источниках:
1) Kaggle (Kaggle API)                 -> нужны env vars KAGGLE_USERNAME / KAGGLE_KEY
2) BigQuery Public Datasets            -> нужны Google ADC creds (см. ниже)
3) Open Data portals на CKAN           -> без ключей, через package_search

Печатает единый список ссылок.

ВАЖНО ПРО СЕКРЕТЫ:
- Kaggle creds держи в env vars Run/Debug, не в .env
- Google creds: лучше Application Default Credentials (ADC)

BigQuery ADC (варианты):
A) gcloud auth application-default login
B) GOOGLE_APPLICATION_CREDENTIALS=path\to\service_account.json
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

import requests

# Kaggle
try:
    from kaggle.api.kaggle_api_extended import KaggleApi
except Exception:
    KaggleApi = None  # type: ignore

# BigQuery
try:
    from google.cloud import bigquery
except Exception:
    bigquery = None  # type: ignore


# ---------------------------- models ----------------------------

@dataclass(frozen=True)
class Hit:
    source: str
    title: str
    url: str
    score_hint: float
    details: str


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


# ---------------------------- Kaggle ----------------------------

def _kaggle_ready() -> Tuple[bool, str]:
    if KaggleApi is None:
        return False, "kaggle package not installed"
    if os.getenv("KAGGLE_USERNAME") and os.getenv("KAGGLE_KEY"):
        return True, ""
    home = os.path.expanduser("~")
    if os.path.exists(os.path.join(home, ".kaggle", "kaggle.json")):
        return True, ""
    return False, "Kaggle creds not found (set env vars KAGGLE_USERNAME/KAGGLE_KEY or ~/.kaggle/kaggle.json)"


def search_kaggle(query: str, limit: int, file_type: Optional[str]) -> List[Hit]:
    ok, why = _kaggle_ready()
    if not ok:
        return [Hit("Kaggle", "SKIPPED", "n/a", 0.0, why)]

    api = KaggleApi()
    api.authenticate()

    # В разных версиях kaggle API метод называется dataset_list (а не datasets_list).
    # Также параметр лимита может называться page_size.
    try:
        results = api.dataset_list(search=query, file_type=file_type, sort_by="hottest", page_size=limit)
    except TypeError:
        # fallback на старую сигнатуру (на всякий случай)
        results = api.dataset_list(search=query, file_type=file_type, sort_by="hottest")

    hits: List[Hit] = []
    for d in results[:limit] if hasattr(results, "__getitem__") else results:
        ref = getattr(d, "ref", None)
        title = getattr(d, "title", None) or ref or "Untitled"
        if not ref:
            continue

        downloads = getattr(d, "downloadCount", None)
        votes = getattr(d, "voteCount", None)
        usability = getattr(d, "usabilityRating", None)

        v = float(votes or 0)
        dl = float(downloads or 0)
        us = float(usability or 0.0)
        score = _clamp((v / 1000.0) + (dl / 50000.0) + us, 0.0, 10.0)

        url = f"https://www.kaggle.com/datasets/{ref}"
        details = f"votes={votes or 'n/a'} downloads={downloads or 'n/a'} usability={usability or 'n/a'}"
        hits.append(Hit("Kaggle", str(title), url, score, details))

    if not hits:
        hits.append(Hit("Kaggle", "No matches found", "n/a", 0.0, "Try broader query (e.g. 'payments')."))

    return hits


# ---------------------------- BigQuery ----------------------------

def _bq_ready() -> Tuple[bool, str]:
    if bigquery is None:
        return False, "google-cloud-bigquery not installed"
    return True, ""


def search_bigquery_public(query: str, limit: int) -> List[Hit]:
    ok, why = _bq_ready()
    if not ok:
        return [Hit("BigQuery", "SKIPPED", "n/a", 0.0, why)]

    try:
        client = bigquery.Client()
    except Exception as e:
        return [Hit("BigQuery", "SKIPPED", "n/a", 0.0, f"BigQuery auth not ready (ADC). Error: {e}")]

    project = "bigquery-public-data"
    q = query.lower().strip()
    hits: List[Hit] = []

    try:
        datasets = list(client.list_datasets(project=project))
    except Exception as e:
        return [Hit("BigQuery", "SKIPPED", "n/a", 0.0, f"Failed to list public datasets. Error: {e}")]

    start = time.time()
    for ds_item in datasets:
        if time.time() - start > 12:
            break

        ds_id = ds_item.dataset_id
        if q and (q in ds_id.lower()):
            url = f"https://console.cloud.google.com/bigquery?project={project}&p={project}&d={ds_id}&page=dataset"
            hits.append(Hit("BigQuery", f"{project}:{ds_id}", url, 2.0, "match=dataset_id"))
            if len(hits) >= limit:
                break
            continue

        try:
            ds = client.get_dataset(f"{project}.{ds_id}")
        except Exception:
            continue

        desc = (ds.description or "").lower()
        if q and (q in desc):
            url = f"https://console.cloud.google.com/bigquery?project={project}&p={project}&d={ds_id}&page=dataset"
            hits.append(Hit("BigQuery", f"{project}:{ds_id}", url, 1.5, "match=description"))
            if len(hits) >= limit:
                break

    if not hits:
        hits.append(Hit("BigQuery", "No matches found (or auth/timebox limited)", "n/a", 0.0, "Try broader query."))

    return hits


# ---------------------------- CKAN (Open Data) ----------------------------

DEFAULT_CKAN_PORTALS = [
    "https://catalog.data.gov",
    "https://open.canada.ca/data/en",
]


def _ckan_search_one(base_url: str, query: str, limit: int) -> List[Hit]:
    api = base_url.rstrip("/") + "/api/3/action/package_search"
    try:
        r = requests.get(api, params={"q": query, "rows": limit}, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data.get("success"):
            return [Hit("CKAN", "SKIPPED", base_url, 0.0, "CKAN API responded success=false")]
        res = data["result"]["results"]
    except Exception as e:
        return [Hit("CKAN", "SKIPPED", base_url, 0.0, f"CKAN request failed: {e}")]

    hits: List[Hit] = []
    for pkg in res:
        title = pkg.get("title") or pkg.get("name") or "Untitled"
        name = pkg.get("name") or ""
        url = base_url.rstrip("/") + "/dataset/" + name if name else base_url
        score = _clamp(float(pkg.get("score", 0.0)), 0.0, 10.0)
        details = f"portal={base_url}"
        hits.append(Hit("OpenData(CKAN)", str(title), url, score, details))
    return hits


def search_ckan_portals(query: str, limit_per_portal: int, portals: List[str]) -> List[Hit]:
    hits: List[Hit] = []
    for p in portals:
        hits.extend(_ckan_search_one(p, query, limit_per_portal))
    return hits


# ---------------------------- CLI / main ----------------------------

def build_cli() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Search datasets across Kaggle, BigQuery public datasets, and CKAN portals.")
    p.add_argument("query", help="Search query, e.g. 'payments transactions subscriptions churn'")
    p.add_argument("--kaggle", action="store_true", help="Enable Kaggle search")
    p.add_argument("--bigquery", action="store_true", help="Enable BigQuery public datasets search")
    p.add_argument("--ckan", action="store_true", help="Enable CKAN open data search")
    p.add_argument("--all", action="store_true", help="Enable all sources (default if none selected)")
    p.add_argument("--limit", type=int, default=15, help="Limit per source (default: 15)")
    p.add_argument("--kaggle-file-type", default="csv", help="Kaggle file_type filter (default: csv). Use '' to disable.")
    p.add_argument("--ckan-portals", default="", help="Comma-separated CKAN portal base URLs. If empty, uses defaults.")
    return p


def main() -> int:
    args = build_cli().parse_args()
    q = args.query.strip()

    enable_any = args.kaggle or args.bigquery or args.ckan or args.all
    if not enable_any:
        args.all = True

    use_kaggle = args.all or args.kaggle
    use_bq = args.all or args.bigquery
    use_ckan = args.all or args.ckan

    limit = max(1, args.limit)

    hits: List[Hit] = []

    if use_kaggle:
        ft = args.kaggle_file_type.strip()
        ft = None if ft == "" else ft
        hits.extend(search_kaggle(q, limit=limit, file_type=ft))

    if use_bq:
        hits.extend(search_bigquery_public(q, limit=limit))

    if use_ckan:
        portals = [p.strip() for p in args.ckan_portals.split(",") if p.strip()] if args.ckan_portals else DEFAULT_CKAN_PORTALS
        hits.extend(search_ckan_portals(q, limit_per_portal=min(limit, 10), portals=portals))

    def key(h: Hit):
        is_skipped = 1 if h.title == "SKIPPED" else 0
        return (is_skipped, -h.score_hint, h.source, h.title)

    hits_sorted = sorted(hits, key=key)

    for i, h in enumerate(hits_sorted, start=1):
        print(f"{i:02d}. [{h.source}] {h.title}")
        print(f"    url: {h.url}")
        if h.details:
            print(f"    details: {h.details}")
        print("")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
