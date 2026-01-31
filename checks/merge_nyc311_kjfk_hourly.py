from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

NOISE = DATA / "nyc311_noise_residential_brooklyn_2023.csv"
WEATHER = DATA / "weather_kjfk_hourly_2023.csv"

# --- Load 311 ---
noise = pd.read_csv(
    NOISE,
    parse_dates=["created_date"],
)

# 311 timestamps are NYC local, naive
noise["hour"] = noise["created_date"].dt.floor("h")

# --- Load weather ---
weather = pd.read_csv(
    WEATHER,
    parse_dates=["hour"],
)

# --- Merge ---
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
