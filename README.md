# NYC 311 × Weather: When time-only joins silently fail (and what we found after fixing it)

RUNNING FILE: C:\Users\User\PycharmProjects\analytics-storytelling\app.py

This is a single-hypothesis story (no ML, no dashboards).

---

## Run locally (from zero)

This project is fully reproducible from a clean environment.

### Requirements
- Python **3.11+**
- Git

### Setup
```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>

python -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\activate

pip install -r requirements.txt
```

### Run
```bash
streamlit run app.py
```

The app expects the canonical dataset at:

```text
data/nyc311_noise_brooklyn_2023_with_weather_canonical.csv
```

If the file is missing or invalid, the app will fail fast with a clear error message.
This is intentional and part of the data contract.

### Notes on reproducibility
- Only **CSV** is used as a data artifact (no pickle/parquet).
- Time alignment and merge validity are documented in `checks/README.md`.
- No ML models or training steps are required.



## Dataset (canonical)

- NYC 311 complaints: Brooklyn · Noise – Residential · 2023 · **86,040 rows**
- Weather: NOAA ISD · Station **KJFK (744860-94789)** · 2023 · **hourly**

---

## Key engineering lesson

My first weather dataset looked clean and hourly, but turned out unusable because it had **no geographic identity**.

This is why **time-only joins silently fail**.

---

## Hypothesis

**Residential noise complaints in Brooklyn increase with temperature — but only during evening and night hours.**

We do **not** claim causality.  
We only check whether the pattern is present in a **contract-valid dataset**.

---

## Conclusion

The hypothesis is **supported**.

- During **daytime**, complaint volume is relatively stable across temperatures.
- During **evening and night**, higher temperatures are associated with a **sharp increase** in complaints.

The signal appears only when weather conditions intersect with human activity patterns.

---

## What we deliberately did NOT do

- No correlation coefficients, p-values, or regressions  
- No ML / prediction  
- No “EDA fishing” with dozens of charts  
- No causal claims

---

PORTFOLIO-2026.02.01 · NYC 311 × NOAA ISD (KJFK) · engineering-first storytelling
