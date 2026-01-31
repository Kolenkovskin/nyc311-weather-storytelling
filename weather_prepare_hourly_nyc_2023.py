"""
WEATHER-PREPARE-NYC-2023 v2026.02.01-02

Reads single NOAA ISD CSV for NYC region (2023),
keeps only analysis-ready hourly columns,
outputs clean CSV for merge with NYC 311 Noise.
"""

from pathlib import Path
import pandas as pd

SRC_FILE = Path(
    "data/weather/2023_lat_39__42__lon_-76__-72_1.1M/"
    "2023_lat_39__42__lon_-76__-72_1.1M.csv"
)

OUT = Path("data/weather_nyc_hourly_2023_clean.csv")

# 1) Load
assert SRC_FILE.exists(), f"Source file not found: {SRC_FILE}"
w = pd.read_csv(SRC_FILE, low_memory=False)

print("Loaded rows:", len(w))
print("Loaded columns:", list(w.columns))

# 2) Detect datetime column
time_col = None
for c in w.columns:
    if c.upper() in ("DATE", "DATETIME", "DATE_TIME"):
        time_col = c
        break

assert time_col is not None, "No datetime column found"

w["datetime"] = pd.to_datetime(w[time_col], errors="coerce", utc=True)

# 3) Keep only storytelling-relevant columns (if present)
KEEP = {
    "TMP": "air_temp_c",
    "DEW": "dew_point_c",
    "SLP": "sea_level_pressure_hpa",
    "WND": "wind_raw",
    "AA1": "precip_raw",
}

cols = {"datetime": "datetime"}
for k, v in KEEP.items():
    if k in w.columns:
        cols[k] = v

w = w[list(cols.keys())].rename(columns=cols)

# 4) Cleanup
w = w.dropna(subset=["datetime"])
w = w.sort_values("datetime").reset_index(drop=True)

# 5) Save
OUT.parent.mkdir(parents=True, exist_ok=True)
w.to_csv(OUT, index=False)

print(f"OK: saved {len(w)} rows -> {OUT}")
print("Columns:", list(w.columns))
print("Time span:", w["datetime"].min(), "→", w["datetime"].max())
