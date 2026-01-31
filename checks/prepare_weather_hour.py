from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

SRC = DATA_DIR / "weather_nyc_hourly_2023_clean.csv"
DST = DATA_DIR / "weather_nyc_hourly_2023_with_hour.csv"

weather = pd.read_csv(
    SRC,
    parse_dates=["datetime"],
)

# Канонический час (pandas 2.x → "h")
weather["hour"] = weather["datetime"].dt.floor("h")

# Контроль инвариантов
print("rows:", len(weather))
print("unique hours:", weather["hour"].nunique())
print("hour min:", weather["hour"].min())
print("hour max:", weather["hour"].max())

assert weather["hour"].nunique() == len(weather), "Hour is not unique!"

weather.to_csv(DST, index=False)
print("saved:", DST)
