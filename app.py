# app.py
# PORTFOLIO-2026.02.01-NYC311-WEATHER-STORYTELLING-03
# One-page Streamlit story (no dashboard vibes, no ML)

from __future__ import annotations

from pathlib import Path
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt


APP_TITLE = "NYC 311 × Weather: When time-only joins silently fail (and what we found after fixing it)"
DATA_CSV = Path("data/nyc311_noise_brooklyn_2023_with_weather_canonical.csv")


def load_canonical() -> pd.DataFrame:
    # Canon: CSV only (portable across environments)
    if not DATA_CSV.exists():
        raise FileNotFoundError(
            "Canonical dataset not found. Expected:\n"
            f"- {DATA_CSV.as_posix()}\n"
        )

    df = pd.read_csv(DATA_CSV, parse_dates=["created_hour"])

    expected = {"created_hour", "temperature_c", "complaint_id"}
    missing = sorted(list(expected - set(df.columns)))
    if missing:
        raise ValueError(f"Canonical dataset missing columns: {missing}")

    df = df.copy()
    df["created_hour"] = pd.to_datetime(df["created_hour"], errors="coerce")
    df["temperature_c"] = pd.to_numeric(df["temperature_c"], errors="coerce")
    df["complaint_id"] = df["complaint_id"].astype(str)

    if df["created_hour"].isna().any():
        raise ValueError("created_hour has NaT values. Fix upstream in preparation notebook.")
    if df["complaint_id"].isna().any():
        raise ValueError("complaint_id has null values. Fix upstream in preparation notebook.")

    return df


def assign_time_bucket(hour: int) -> str:
    if 8 <= hour <= 17:
        return "Day"
    if 18 <= hour <= 22:
        return "Evening"
    return "Night"


def build_agg(df: pd.DataFrame, bin_size_c: int) -> pd.DataFrame:
    dfx = df.dropna(subset=["temperature_c"]).copy()
    dfx["hour"] = dfx["created_hour"].dt.hour
    dfx["time_bucket"] = dfx["hour"].apply(assign_time_bucket)

    dfx["temp_bin"] = ((dfx["temperature_c"] // bin_size_c) * bin_size_c).astype("Int64")

    agg = (
        dfx.dropna(subset=["temp_bin"])
        .groupby(["time_bucket", "temp_bin"])
        .agg(complaints_count=("complaint_id", "count"))
        .reset_index()
        .sort_values(["time_bucket", "temp_bin"])
    )
    return agg


def plot_main(agg: pd.DataFrame) -> plt.Figure:
    fig = plt.figure(figsize=(8, 5))
    for bucket in ["Day", "Evening", "Night"]:
        sub = agg[agg["time_bucket"] == bucket]
        plt.plot(sub["temp_bin"], sub["complaints_count"], marker="o", label=bucket)

    plt.xlabel("Temperature (°C, binned)")
    plt.ylabel("Number of complaints")
    plt.title("Residential noise complaints vs temperature by time of day (Brooklyn, 2023)")
    plt.legend()
    plt.tight_layout()
    return fig


def main() -> None:
    st.set_page_config(page_title="NYC 311 × Weather", layout="centered")
    st.title(APP_TITLE)

    st.markdown(
        """
This is a **single-hypothesis story** (no ML, no dashboards).

**Dataset (canonical):**
- NYC 311 complaints: Brooklyn · Noise – Residential · 2023 · 86,040 rows  
- Weather: NOAA ISD · Station KJFK (744860-94789) · 2023 · hourly

**Key engineering lesson:**
> My first weather dataset looked clean and hourly, but turned out unusable because it had no geographic identity.  
> This is why time-only joins silently fail.
"""
    )

    st.divider()

    # Sidebar controls (minimal, not dashboard-ish)
    st.sidebar.header("Controls")
    bin_size_c = st.sidebar.selectbox("Temperature bin size (°C)", [2, 3, 4, 5], index=1)

    # Load data
    try:
        df = load_canonical()
    except Exception as e:
        st.exception(e)
        st.stop()

    coverage = 1.0 - float(df["temperature_c"].isna().mean())

    with st.expander("Data contract (why this analysis is valid)", expanded=False):
        st.markdown(
            f"""
- Complaint timestamps are **NYC local time (naive)**
- Weather timestamps are **NYC local time (naive)** derived from UTC with DST handled upstream
- Weather is **station-specific (KJFK)** → has geographic identity
- Join is **m:1 by local hour** (many complaints per hour, one weather record)
- Weather coverage after join: **{coverage:.2%}**
"""
        )

    st.subheader("Hypothesis")
    st.markdown(
        """
**Residential noise complaints in Brooklyn increase with temperature — but only during evening and night hours.**

I do **not** claim causality. I only check whether the pattern is present in a contract-valid dataset.
"""
    )

    agg = build_agg(df, bin_size_c=bin_size_c)

    st.subheader("Evidence")
    fig = plot_main(agg)
    st.pyplot(fig)

    st.subheader("Conclusion")
    st.markdown(
        """
The hypothesis is **supported**.

- During **daytime**, complaint volume is relatively stable across temperatures.
- During **evening and night**, higher temperatures are associated with a sharp increase in complaints.

The signal appears only when weather conditions intersect with human activity patterns.
"""
    )

    with st.expander("What I deliberately did NOT do", expanded=False):
        st.markdown(
            """
- No correlation coefficients, p-values, or regressions  
- No ML / prediction  
- No “EDA fishing” with dozens of charts  
- No causal claims  
"""
        )

    st.caption("PORTFOLIO-2026.02.01 · NYC 311 × NOAA ISD (KJFK) · engineering-first storytelling")


if __name__ == "__main__":
    main()
