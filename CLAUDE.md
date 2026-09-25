# CLAUDE.md

Standards for every file in this repository. They come from `reference/pipelines/`, with its twelve known defects removed. Read this before you write code or lesson content.

## Project

A static, offline-capable learning web app (GitHub Pages, PWA, Pyodide) with four tracks: A Databricks pipeline engineering, B Python for data science, C Microsoft Fabric, D Finding errors in code. Lesson content lives in `content/` and drives both the app and the handbook. Never write lesson text twice.

## Writing style for lesson content

- British English. Short sentences. Active voice. Address the reader as "you".
- No filler, no em dashes, no hype words.
- One idea per lesson. Concept section: 150 to 300 words.
- Every claim about an API names the version it applies to. Every Fabric feature carries its status (GA or preview) from `VERSIONS.md`.
- Never invent a function, parameter or config key. If you have not checked it against official docs, mark it `unverified: true` in the lesson file and list it in `VERSIONS.md`.

## Python and PySpark standards

These are the "strong code" side of every worked example.

### Structure
- Small, single-purpose functions. One function does one step: read, transform, validate, write or log.
- Type hints on every parameter and return value. Use built-in generics (`list[str]`, `dict[str, int]`) and `X | None`. Never `param: str = None`.
- A docstring on every public function and class: one-line summary, then Args, Returns, Raises (Google style).
- No module-level side effects. Do not call `SparkSession.builder.getOrCreate()` at import time. Pass `spark` as a parameter or get it inside a function, so tests inject a local session.
- Constants in `UPPER_SNAKE_CASE` at module top. Classes in `PascalCase`. Functions and variables in `snake_case`.
- Prefer `Literal` or `Enum` over free strings for status and severity values.

### Imports
- `from pyspark.sql import functions as F` and `from pyspark.sql import types as T`. Never import `sum`, `min`, `max`, `round`, `abs` or `filter` from `pyspark.sql.functions` by name. They shadow Python built-ins.
- Import everything you use. `ruff` (rule F821) catches undefined names.
- `datetime.now(timezone.utc)`, never `datetime.utcnow()` (deprecated in Python 3.12).

### Configuration
- Config-driven parameters. Column maps, type maps, thresholds, table names and contract rules load at runtime from registry tables or versioned JSON/YAML files. Never hardcode them in transformation code.
- Validate config on load (pydantic model or dataclass with checks). Fail fast on a missing key.
- No secrets, workspace URLs, storage keys or personal data in code. Use Databricks secret scopes or environment variables.

### Medallion layers
- Document the grain of every table in its docstring and in a table comment or `TBLPROPERTIES`.
- Bronze: append-only. Preserve the delivery as received. Add audit columns: `ingestion_id`, `source_file`, `ingestion_timestamp`, `delivery_version`.
- Silver: canonical names and types from the registry. Deduplicate the source on the merge keys before `MERGE`. Idempotent `MERGE` on redelivery.
- Gold: aggregated, business-ready, grain stated. Group by every grain column the docstring names.
- Naming: notebook `[layer]_[tracker]_[action]`, bronze `[tracker]_raw`, silver `[tracker]_respondents`, gold `[tracker]_metrics`, job `[tracker]_[layer]_pipeline`.

### Data quality and observability
- Every run appends one record to a Delta run log table with an explicit schema (`StructType`), a UTC timestamp and a `run_id`.
- QA results are structured records (dataclass or Row), never narrative text.
- Severity: CRITICAL halts the pipeline (raise). WARN logs and continues.
- Guard every division: empty DataFrames, zero totals, null aggregates.
- Test for `None` with `is None`. Never use truthiness on a number that is allowed to be `0.0`.
- Compute several counts in one `agg` pass. Do not call `count()` repeatedly on an uncached DataFrame.
- Filter boolean columns directly: `F.col("in_scope")`, never `== True` (ruff E712).

### Incremental processing
- Load only waves or files not yet in the target layer. Filter both sides of the comparison on the same keys (for example `tracker_id`).
- Prefer Auto Loader or change data feed where the source supports it.

### Unity Catalog SQL
- Three-level names: `catalog.schema.table`.
- Row filters: a SQL UDF plus `ALTER TABLE ... SET ROW FILTER`. Column masks: `ALTER TABLE ... ALTER COLUMN ... SET MASK`. `CREATE ROW ACCESS POLICY` is Snowflake syntax and does not exist in Databricks.
- Prefer `is_account_group_member()` over `is_member()` in Unity Catalog.
- Grant to groups, never to individual users.

## Tooling and quality gates

- `ruff check` and `ruff format` on all Python. `mypy --strict` on `scripts/`, `checkers/` and `practice/`.
- Every reference solution passes its checker. Every seeded bug fails its checker. Every listed wrong answer triggers its feedback. `pytest tests/content` enforces all three.
- Regenerate the handbook (`python scripts/build_handbook.py`) after every content change and commit the output.
- Test the app at 390px width.

## Seed material for Track D

`reference/pipelines/README.md` lists twelve known defects. Keep them out of every "strong code" example. Reuse them as spot-the-bug and review exercises in Track D.

## Git

- Work on the branch the session names. Commit at the end of each build phase with a clear message.
