# PR #214: Add wave stability check, gold region join and redelivery MERGE

Author: coding assistant (drafted from a one-line request). Target branch: `main`.

## Description (as written by the assistant)

> This PR adds a wave-over-wave stability check, joins region names into gold, updates the silver
> MERGE for redeliveries and adds an API helper for wave metadata. All tests pass. The code follows
> the team standard and has been tested thoroughly.

## Files changed

### 1. `pipelines/qa_statistical.py`

```python
def stability_status(current_pct: float | None, prior_pct: float | None, tolerance: float = 0.10) -> str:
    """Return WARN if the share moved more than tolerance, PASS if not, SKIP if missing."""
    if current_pct and prior_pct:
        return "WARN" if abs(current_pct - prior_pct) > tolerance else "PASS"
    return "SKIP"
```

### 2. `pipelines/gold_metrics.py`

```python
from pyspark.sql import functions as F

def add_region_names(gold: DataFrame, regions: DataFrame) -> DataFrame:
    """Attach region names. One row per gold row."""
    return gold.join(regions, "region_code")
```

### 3. `sql/silver_merge.sql`

```sql
MERGE INTO research.research_silver.nat_respondents AS t
USING research.research_bronze.nat_latest AS s
ON t.respondent_id = s.respondent_id
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *;
```

### 4. `tests/test_qa_statistical.py`

```python
def test_stability_status():
    current, prior, tol = 0.30, 0.10, 0.10
    expected = "WARN" if abs(current - prior) > tol else "PASS"
    assert stability_status(current, prior, tol) == expected
```

### 5. `pipelines/wave_api.py`

```python
import requests

API_TOKEN = "tok_EXAMPLE_not_real_0000"

def fetch_wave(wave_id: str) -> dict[str, object]:
    """Fetch wave metadata from the survey platform."""
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    return requests.get(f"https://survey.example/api/waves/{wave_id}", headers=headers, timeout=30).json()
```

## Your task

Review it as you would a colleague's pull request. For each file, record the defect, its severity
(blocking or not), and the fix you would request. Then give a verdict. Use `REVIEW_TEMPLATE.md`.
Grade yourself in the app: lesson X3-L1 holds the same hunks, with the answer key hidden until you
submit.
