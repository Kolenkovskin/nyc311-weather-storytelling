from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

SRC = DATA_DIR / "weather_nyc_hourly_2023_clean.csv"
DST = DATA_DIR / "weather_nyc_hourly_2023_hourly.csv"

weather = pd.read_csv(
    SRC,
    parse_dates=["datetime"],
)

# 1) UTC → NYC → naive
weather["datetime"] = (
    weather["datetime"]
    .dt.tz_convert("America/New_York")
    .dt.tz_localize(None)
)

# 2) Только 2023 (local)
weather = weather[
    (weather["datetime"] >= "2023-01-01 00:00:00") &
    (weather["datetime"] <= "2023-12-31 23:59:59")
]

# 3) Канонический час
weather["hour"] = weather["datetime"].dt.floor("h")

# 4) Типы
NUM_COLS = [
    "air_temp_c",
    "dew_point_c",
    "sea_level_pressure_hpa",
]

for col in NUM_COLS:
    weather[col] = pd.to_numeric(weather[col], errors="coerce")

# 5) Агрегация
agg = (
    weather
    .groupby("hour", as_index=False)
    .agg({
        "air_temp_c": "mean",
        "dew_point_c": "mean",
        "sea_level_pressure_hpa": "mean",
    })
)

# 6) ИСТИННЫЕ инварианты
print("rows:", len(agg))
print("unique hours:", agg["hour"].nunique())
print("hour min:", agg["hour"].min())
print("hour max:", agg["hour"].max())

assert agg["hour"].is_unique
assert agg["hour"].dt.tz is None
assert agg["hour"].min().year == 2023
assert agg["hour"].max().year == 2023

agg.to_csv(DST, index=False)
print("saved:", DST)
