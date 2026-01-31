from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

SRC = DATA / "74486094789.csv"
DST = DATA / "weather_kjfk_hourly_2023.csv"

df = pd.read_csv(
    SRC,
    parse_dates=["DATE"],
)

# --- Parse physics ---
tmp = df["TMP"].str.split(",", expand=True)
df["air_temp_raw"] = pd.to_numeric(tmp[0], errors="coerce")
df.loc[df["air_temp_raw"] == 9999, "air_temp_raw"] = pd.NA
df["air_temp_c"] = df["air_temp_raw"] / 10

slp = df["SLP"].str.split(",", expand=True)
df["slp_raw"] = pd.to_numeric(slp[0], errors="coerce")
df.loc[df["slp_raw"] == 99999, "slp_raw"] = pd.NA
df["slp_hpa"] = df["slp_raw"] / 10

# --- Time contract ---
# NOAA ISD timestamps are UTC
df["datetime_utc"] = df["DATE"].dt.tz_localize("UTC")

# Convert to NYC local time, then make naive
df["datetime_local"] = (
    df["datetime_utc"]
    .dt.tz_convert("America/New_York")
    .dt.tz_localize(None)
)

df["hour"] = df["datetime_local"].dt.floor("h")

# Keep only local 2023
df = df[
    (df["hour"] >= "2023-01-01 00:00:00") &
    (df["hour"] <= "2023-12-31 23:59:59")
]

# --- Hourly aggregation ---
agg = (
    df
    .groupby("hour", as_index=False)
    .agg({
        "air_temp_c": "mean",
        "slp_hpa": "mean",
    })
)

# --- Invariants ---
print("rows:", len(agg))
print("unique hours:", agg["hour"].nunique())
print("hour min:", agg["hour"].min())
print("hour max:", agg["hour"].max())
print("temp missing %:", round(agg["air_temp_c"].isna().mean() * 100, 2))

assert agg["hour"].is_unique
assert agg["hour"].dt.tz is None
assert agg["hour"].min().year == 2023
assert agg["hour"].max().year == 2023

agg.to_csv(DST, index=False)
print("saved:", DST)
