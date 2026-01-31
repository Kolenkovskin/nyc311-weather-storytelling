from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

NOISE_FILE = DATA_DIR / "nyc311_noise_residential_brooklyn_2023.csv"
WEATHER_FILE = DATA_DIR / "weather_nyc_hourly_2023_clean.csv"

print("Project root:", ROOT)
print("Loading datasets...")

noise = pd.read_csv(
    NOISE_FILE,
    parse_dates=["created_date"],
)

weather = pd.read_csv(
    WEATHER_FILE,
    parse_dates=["hour"],
)

print("\n=== NOISE ===")
print("rows:", len(noise))
print("created_date min:", noise["created_date"].min())
print("created_date max:", noise["created_date"].max())

print("\n=== WEATHER ===")
print("rows:", len(weather))
print("hour min:", weather["hour"].min())
print("hour max:", weather["hour"].max())

print("\n=== WEATHER uniqueness check ===")
print("unique hours:", weather["hour"].nunique())

print("\n=== TIMEZONE CHECK (dtype) ===")
print("noise created_date dtype:", noise["created_date"].dtype)
print("weather hour dtype:", weather["hour"].dtype)
