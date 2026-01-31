from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

NOISE = DATA_DIR / "nyc311_noise_residential_brooklyn_2023.csv"
WEATHER = DATA_DIR / "weather_nyc_hourly_2023_hourly.csv"

noise = pd.read_csv(
    NOISE,
    parse_dates=["created_date"],
)

# 1) 311: считаем UTC → NYC → naive
noise["created_date"] = (
    noise["created_date"]
    .dt.tz_localize("UTC")
    .dt.tz_convert("America/New_York")
    .dt.tz_localize(None)
)

noise["hour"] = noise["created_date"].dt.floor("h")

weather = pd.read_csv(
    WEATHER,
    parse_dates=["hour"],
)

merged = noise.merge(
    weather,
    on="hour",
    how="left",
)

print("=== BASIC COUNTS ===")
print("311 rows:", len(noise))
print("merged rows:", len(merged))

print("\n=== WEATHER COVERAGE ===")
missing = merged["air_temp_c"].isna().mean() * 100
print("missing weather %:", round(missing, 2))

print("\n=== TEMPERATURE SANITY ===")
print(merged["air_temp_c"].describe())

print("\n=== DATE SANITY ===")
print("hour min:", merged["hour"].min())
print("hour max:", merged["hour"].max())

assert len(merged) == len(noise)
