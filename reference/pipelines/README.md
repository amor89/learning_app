# Reference pipeline code

Source: the pipeline improvement project for a multi-tracker survey programme on Azure Databricks. Names are generic (tracker "NAT", schema `research_*`). No credentials, workspace URLs or personal data.

## Files

| File | Covers |
|---|---|
| bronze_ingest.py | Append-only ingestion with audit columns |
| silver_transform.py | Registry-driven column maps, type casting, MERGE on redelivery |
| gold_metrics.py | Weighted reach metrics at wave x subgroup grain |
| observability.py | Run log table, table health checks, incremental wave detection |
| data_contracts.py | Contract validator with severity levels and structured results |
| qa_statistical.py | Weight distribution and wave-over-wave stability checks |
| unity_catalog.sql | Layer permissions, table properties, row-level security |
| contracts/nat_contract_v2.json | Example data contract |

## Standards to extract for CLAUDE.md

- Medallion layers with a documented grain per table. Bronze append-only. Silver MERGE. Gold aggregated.
- Type hints and a docstring on every function. Small single-purpose functions.
- Config and column maps loaded at runtime from registry tables, never hardcoded.
- Every run logged to a Delta table. QA results stored as structured records.
- CRITICAL checks halt the pipeline. WARN checks log and continue.
- Incremental processing: load only waves not yet in the target layer.

## Naming conventions

| Object | Convention | Example |
|---|---|---|
| Notebook | [layer]_[tracker_short]_[action] | silver_nat_transform |
| Bronze table | [tracker_short]_raw | nat_raw |
| Silver table | [tracker_short]_respondents | nat_respondents |
| Gold table | [tracker_short]_metrics | nat_metrics |
| Job | [tracker_short]_[layer]_pipeline | nat_silver_pipeline |
| Functions / classes / constants | snake_case / PascalCase / UPPER_SNAKE_CASE | check_table_health / CheckResult / MAX_WEIGHT_CV |

## Known defects, kept on purpose

This code was written with Claude and never ran through a linter or test suite. Do not copy these into the standard. Use them as seed material for Track D (finding errors in code, including Claude's).

1. observability.py uses `uuid` and `datetime` without importing them. NameError on the first run.
2. data_contracts.py imports PySpark `sum`, which shadows the Python built-in. `pass_rate` then calls the Spark function on a generator and fails.
3. gold_metrics.py and qa_statistical.py shadow `sum` the same way. Safer: `from pyspark.sql import functions as F`.
4. unity_catalog.sql uses `CREATE ROW ACCESS POLICY`, which is Snowflake syntax. Databricks uses a SQL UDF plus `ALTER TABLE ... SET ROW FILTER`.
5. `load_column_map` accepts `wave_id` but never uses it, and reads a `source_column` field missing from the Variable Registry schema.
6. `datetime.utcnow()` is deprecated from Python 3.12. Use `datetime.now(timezone.utc)`.
7. `error_message: str = None` should be `str | None = None`.
8. `qa_statistical.check_wave_stability` uses `if current_pct and prior_pct`, which skips a legitimate 0.0 proportion.
9. `_check_distributions` divides by `total` with no guard for an empty DataFrame.
10. `get_unprocessed_waves` compares bronze waves for one tracker against silver waves for all trackers, since silver has no tracker filter.
11. The validator calls `df.count()` several times on an uncached DataFrame, which rescans the source on each call.
12. `== True` comparisons in filters trip ruff rule E712. Use the column directly.
