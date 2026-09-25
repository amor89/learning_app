# Versions

Checked on 25 September 2026. Status key:
- Verified: confirmed against an official source (PyPI, Databricks docs, Microsoft Learn or the Fabric blog).
- Search only: confirmed through search results that quote the official page. The page itself was blocked by this build environment's network policy. Re-check when access is open.
- Unverified: not yet confirmed. Do not teach it as fact until checked.

## Platforms

| Item | Version | Status | Source |
|---|---|---|---|
| Databricks Runtime LTS (target for lessons) | 17.3 LTS, Apache Spark 4.0.0, released October 2025 | Search only | docs.databricks.com/aws/en/release-notes/runtime/17.3lts |
| Databricks Runtime 18 LTS | Apache Spark 4.1.0, JDK 21, unified release with dated updates | Search only. Search results describe it as "in feature development". Confirm its LTS status before switching lessons to it. | docs.databricks.com/aws/en/release-notes/runtime/18 |
| Databricks Runtime 16.4 LTS | Apache Spark 3.5.2 | Search only | docs.databricks.com/aws/en/release-notes/runtime/16.4lts |
| Python on DBR 17.3 LTS | Unverified | Unverified | Check the "System environment" section of the 17.3 LTS release notes |
| pandas, scikit-learn on DBR 17.3 LTS ML | Unverified | Unverified | requirements-cpu-17.3lts.txt from the ML release notes |
| Databricks Free Edition | Serverless compute only, per-account quotas, one workspace, Python and SQL notebooks (no Scala or R), restricted outbound internet | Search only | docs.databricks.com/aws/en/getting-started/free-edition-limitations |
| Fabric Runtime 2.0 | Spark 4.1, Delta Lake 4.2, Java 21, Python 3.13. GA, not yet the default runtime | Search only | learn.microsoft.com/en-us/fabric/data-engineering/runtime-2-0 |
| Fabric default runtime | Unverified (1.3 expected) | Unverified | learn.microsoft.com/en-us/fabric/data-engineering/runtime |

## Python packages (latest on PyPI)

| Package | Latest | Pin for this project | Status |
|---|---|---|---|
| pandas | 3.0.6 | 3.0.x for Track B, with notes where 2.x behaviour differs (Copy-on-Write, string dtype) | Verified (PyPI) |
| Polars | 1.44.2 | 1.44.x | Verified (PyPI) |
| scikit-learn | 1.9.1 | 1.9.x | Verified (PyPI) |
| NumPy | 2.5.3 | 2.x (2.4.6 resolved locally alongside scikit-learn 1.9.1) | Verified (PyPI) |
| DuckDB | 1.5.5 | 1.5.x | Verified (PyPI) |
| pandera | 0.33.1 | 0.33.x | Verified (PyPI) |
| pydantic | 2.13.5 | 2.x | Verified (PyPI) |
| PySpark (local harness) | 4.2.0 latest. 4.0.4 matches DBR 17.3 LTS | 4.0.4 | Verified (PyPI) |
| delta-spark (local harness) | 4.4.0 latest. 4.0.1 pairs with Spark 4.0 | 4.0.1 | Verified: `pytest practice --solutions` passes with PySpark 4.0.4 and delta-spark 4.0.1 on Java 21 |
| ruff | 0.16.9 | 0.16.x | Verified (PyPI) |
| mypy | 2.3.1 | 2.3.x | Verified (PyPI) |
| pytest | 9.1.1 | 9.x | Verified (PyPI) |
| python-docx | 1.2.0 | 1.2.x | Verified (PyPI) |
| WeasyPrint (PDF build) | 70.0 | 70.x | Verified (PyPI) |

## Browser runtime

| Item | Version | Status | Notes |
|---|---|---|---|
| Pyodide | 314.0.7 | Verified (npm package and its pyodide-lock.json) | Bundles Python 3.14.2, pandas 3.0.2, NumPy 2.4.6, scikit-learn 1.8.0. CDN path `https://cdn.jsdelivr.net/pyodide/v314.0.7/full/` taken from the package's own loader. Pyodide 314 runs in module workers only. |

Browser exercises run on the Pyodide versions. Laptop and CI tests run on the pins above. The pandas behaviour taught in Track B is the same in 3.0.2 and 3.0.6.

## Fabric feature status

Every Track C lesson cites a row in this table. Microsoft Learn pages were blocked in this build environment, so each row needs a direct page check before Phase 4.

| Feature | Status | Check |
|---|---|---|
| Mirroring Azure Databricks Unity Catalog | GA | Search only (Fabric blog GA announcement) |
| Mirroring Azure Databricks behind private endpoints | GA | Search only (Fabric blog) |
| Fabric data agent | GA | Search only (Learn: concept-data-agent) |
| Data agent in Microsoft 365 Copilot, Copilot Studio, Copilot in Power BI | Preview | Search only (Learn page titles carry "preview") |
| OneLake security (roles to row and column level) | Unverified | Unverified |
| Fabric IQ | Unverified | Unverified |
| Copilot in notebooks (data access limited to the notebook's attached data) | Documented behaviour. GA status unverified | Search only |
| OneLake shortcuts, Direct Lake, Eventstream, Eventhouse, Activator, Dataflows Gen2, copy job, deployment pipelines, Git integration, domains, sensitivity labels | Unverified | Check each in Phase 4 |

## Known platform behaviours to verify before teaching

- Serverless compute (and so Free Edition) does not support `df.cache()` / `persist()` or the classic Spark UI. Unverified. Affects A5 and D2 practicals.
- `owner` is a reserved table property in Spark and fails in `SET TBLPROPERTIES`. Unverified. Affects `reference/pipelines/unity_catalog.sql` and A4.
- MERGE fails with a multiple-source-rows error when two source rows match one target row. Verified locally by `practice/tests/test_a3_l1_merge.py` on delta-spark 4.0.1.
- Spark 4.0 turns ANSI mode on by default, so an invalid `cast` raises an error instead of returning null. Unverified for DBR 17.3 LTS. Affects A2 and D3.

## Track A facts

Checked on 25 September 2026. "Local" means run on PySpark 4.0.4 with delta-spark 4.0.1 (script in `practice/`). "Search" means confirmed through search results quoting docs.databricks.com, which this build environment cannot open directly.

| Fact | Status | Evidence |
|---|---|---|
| Spark 4.0 sets `spark.sql.ansi.enabled=true`. `cast('abc' as int)` raises `CAST_INVALID_INPUT`. `try_cast` returns NULL. | Verified | Local |
| `spark.sql.autoBroadcastJoinThreshold` defaults to 10 MB (10485760 bytes). AQE is on by default. | Verified | Local |
| Appending a DataFrame with an extra column to a Delta table fails with a schema mismatch. `mergeSchema=true` adds the column. A missing column is filled with NULL. A type clash fails with `DELTA_FAILED_TO_MERGE_FIELDS`. | Verified | Local |
| `DESCRIBE HISTORY`, `versionAsOf`, `VERSION AS OF`, `RESTORE TABLE ... TO VERSION AS OF`, `OPTIMIZE ... ZORDER BY` work in Delta 4.0. | Verified | Local |
| `VACUUM ... RETAIN 0 HOURS` fails the retention safety check. Default retention (`delta.deletedFileRetentionDuration`) is 7 days. | Verified (check); Search (7 days) | Local; docs.databricks.com/aws/en/delta/optimize |
| `owner` is a reserved table property: `UNSUPPORTED_FEATURE.SET_TABLE_PROPERTY`. | Verified | Local |
| CHECK constraints fail with `DELTA_VIOLATE_CONSTRAINT_WITH_VALUES`; NOT NULL with `DELTA_NOT_NULL_CONSTRAINT_VIOLATED`. | Verified | Local |
| Change data feed: `delta.enableChangeDataFeed`, `readChangeFeed`, `startingVersion`, `table_changes()`, `_change_type` values `insert`, `update_preimage`, `update_postimage`, `delete`. | Verified | Local and search |
| A Python UDF shows as `BatchEvalPython` in the physical plan. `F.broadcast` gives `BroadcastHashJoin`; with broadcast off, `SortMergeJoin`. | Verified | Local |
| `row_number()` without ORDER BY in the window fails. | Verified | Local |
| `F.col("b") == None` matches no rows. Join on NULL keys matches nothing; `eqNullSafe` matches. | Verified | Local |
| `createDataFrame` from dicts fails with `CANNOT_DETERMINE_TYPE` when a column holds only None. | Verified | Local |
| `withColumnRenamed` on a missing column is a silent no-op. | Verified | Local |
| `pyspark.testing.assertDataFrameEqual` (with `checkRowOrder`, `rtol`, `atol`) and `assertSchemaEqual` exist. | Verified | Local |
| Open-source Spark defaults `saveAsTable` to Parquet. Databricks defaults to Delta. The practice harness sets `spark.sql.sources.default=delta`. | Verified (OSS) | Local |
| Serverless compute (and so Free Edition) does not support `cache()`, `persist()` or SQL `CACHE`. The Spark UI is replaced by the query profile. | Search | docs.databricks.com/aws/en/compute/serverless/limitations |
| Row filters: SQL UDF returning BOOLEAN, applied with `ALTER TABLE ... SET ROW FILTER f ON (col)`. Column masks: `ALTER TABLE ... ALTER COLUMN c SET MASK f`. | Search | docs.databricks.com/aws/en/data-governance/unity-catalog/filters-and-masks/manually-apply |
| `is_account_group_member()` checks account-level groups, directly or indirectly. | Search | docs.databricks.com/aws/en/sql/language-manual/functions/is_account_group_member |
| UC privileges `USE CATALOG`, `USE SCHEMA`, `SELECT`, `MODIFY`; grants on a schema inherit to current and future tables. | Search | docs.databricks.com/aws/en/data-governance/unity-catalog/manage-privileges/ |
| Auto Loader: `cloudFiles.schemaLocation`, `_rescued_data`, `cloudFiles.schemaEvolutionMode` (for example `rescue`, `addNewColumns`), `trigger(availableNow=True)`. | Search | docs.databricks.com/aws/en/ingestion/cloud-object-storage/auto-loader/schema |
| Lakeflow Spark Declarative Pipelines expectations: `@dp.expect`, `@dp.expect_or_drop`, `@dp.expect_or_fail` from `pyspark.pipelines`. | Search | docs.databricks.com/aws/en/ldp/developer/ldp-python-ref-expectations |
| Databricks Asset Bundles were renamed Declarative Automation Bundles on 16 March 2026. The `databricks bundle` CLI and `databricks.yml` are unchanged. | Search | docs.databricks.com/aws/en/release-notes/dev-tools/bundles |
| Bundle variables resolve in order: `--var`, `BUNDLE_VAR_` environment variables, `variable-overrides.json`, target mappings, default. | Search | docs.databricks.com/aws/en/dev-tools/bundles/variables |
| Job parameters read in notebooks with `dbutils.widgets.get`; dynamic value references such as `{{job.run_id}}` use double braces and are not expressions. | Search | docs.databricks.com/aws/en/jobs/parameter-use |
| Git folders: one branch per developer under `/Workspace/Users/`; production Git folders updated only by automation. | Search | docs.databricks.com/aws/en/repos/ci-cd |
| Liquid clustering `CLUSTER BY` / `CLUSTER BY AUTO` and predictive optimization for UC managed tables. | Search | docs.databricks.com/aws/en/tables/clustering |
| PySpark 4.0.4 with pandas 3.0.6 fails on `pyspark.testing.assertDataFrameEqual` and pandas-on-Spark imports: `ImportError: cannot import name '_builtin_table' from 'pandas.core.common'`. With pandas 2.3.3 it works. The `spark` dependency group pins pandas 2.x and runs in its own environment. | Verified | Local |
| `assertDataFrameEqual` ignores row order by default (`checkRowOrder=False`), compares floats with `rtol=1e-5`, fails on schema differences such as INT against BIGINT (`DIFFERENT_SCHEMA`) and on duplicate rows. `PySparkAssertionError` subclasses `AssertionError`. | Verified | Local, pandas 2.3.3 |
| pytest 9.0.2, pydantic 2.12.5, Polars 1.33.1, DuckDB 1.5.1, SciPy 1.18.0, statsmodels 0.14.6 ship with Pyodide 314.0.7. Hypothesis and pandera do not. | Verified | pyodide-lock.json |
