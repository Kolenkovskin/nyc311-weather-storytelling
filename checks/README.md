# Data Checks (Contract Validity)

This folder documents **data validity checks** that justify why the analytical conclusions
in this project can be trusted.

These checks are **not analysis** and **not visualization**.
They exist to validate the **data contract** before any hypothesis is tested.

---

## 1. Time Alignment (`time_alignment`)

### Purpose
Ensure that NYC 311 complaints and weather observations are aligned
on the **same temporal scale**.

This project joins:
- NYC 311 complaints → `created_date`
- NOAA weather → `datetime` (hourly)

A time-only join is dangerous if alignment is inconsistent.

### What is verified
- All timestamps are converted to **UTC**
- Both datasets are **floored to the same hour boundary**
- No systematic ±1 hour shift exists
- The overlap window between datasets is valid

### Typical checks
- Min / max datetime in both datasets
- Hour-of-day distribution (0–23) before merge
- Count and percentage of complaints with **missing weather after merge**

---

## 2. Merge Validation (`merge_validation`)

### Purpose
Ensure that the dataset merge does **not introduce artifacts**
that could create a false pattern.

### What is verified
- Row count before and after merge
- No row duplication introduced by the join
- Join keys behave as **one-to-many**, not many-to-many
- Share of `NaN` values introduced by merge is acceptable and expected

### Why this matters
A broken merge can:
- Artificially amplify counts
- Hide missing data
- Create correlations that do not exist in reality

---

## Why these checks matter

Without documented checks:
> “This is just a nice-looking chart.”

With checks:
> “This result is contract-valid and reproducible.”

These checks ensure that the observed pattern reflects
**real data structure**, not technical error.

---

## Status

- Checks are currently **documented conceptually**
- Full executable validation code is optional and can be added later
- This documentation is sufficient to justify public presentation of results
