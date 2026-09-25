# Phase 0 proposal: architecture and syllabus

## 1. Architecture

### 1.1 Repository layout

```
learning_app/
├── CLAUDE.md                 coding and content standards
├── VERSIONS.md               pinned versions and feature status
├── reference/                your pipeline code and roadmap (read-only)
├── content/                  single source of truth for app and handbook
│   ├── roadmap.yaml          month bands and tagging rules
│   └── tracks/
│       └── A/
│           ├── track.yaml    title, order, checklist for the handbook
│           └── A1/
│               ├── module.yaml       title, roadmap tags, badge
│               └── A1-L1.yaml        one lesson: concept, why, example, exercises, recap
├── checkers/                 Python package: exercise checkers (runs in Pyodide and CPython)
├── site/                     the static app served by GitHub Pages
│   ├── index.html
│   ├── app/                  engine: router, renderers, storage, review deck (ES modules, no framework)
│   ├── vendor/               pinned third-party scripts (Markdown renderer, highlighter)
│   ├── content/              generated JSON bundle (built from content/)
│   ├── downloads/            generated handbook PDF, .docx and notebooks (committed)
│   ├── manifest.webmanifest
│   └── sw.js                 service worker
├── scripts/
│   ├── build_content.py      validate YAML with pydantic, emit site/content/*.json
│   ├── build_handbook.py     PDF (WeasyPrint) and .docx (python-docx) at three levels
│   └── build_notebooks.py    .ipynb per PySpark practical, Fabric lab notebooks
├── practice/                 local pytest harness with a local SparkSession and Delta
└── tests/
    ├── content/              quality gates for every exercise
    └── app/                  Playwright checks at 390px
```

### 1.2 Content format

You author lessons in YAML. YAML block scalars hold code and Markdown without escaping. A build script validates every file against a pydantic schema and emits one JSON bundle per module. The app reads JSON. The handbook reads the same YAML through the same loader. Text exists once.

A new lesson needs one new YAML file and a rebuild. The engine never changes.

Lesson schema (abridged):

```yaml
id: A5-L2
title: Built-in functions over Python UDFs
roadmap: [M16-18, current-work]
concept: |            # Markdown, 150 to 300 words (checked at build)
why_it_matters: |     # one real production failure
worked_example:
  language: python
  weak:   { code: |, annotations: [{line: 3, note: ...}] }
  strong: { code: |, annotations: [...] }
exercises:            # at least 5, rising difficulty (checked at build)
  - id: A5-L2-E1
    type: mcq | fill_gap | write_function | predict_output | spot_bug | refactor | order | design
    difficulty: 1-5
    prompt: |
    checker: {...}          # type-specific
    wrong_answers:          # each maps a matcher to a message
      - match: {...}
        feedback: ...
    hints: [tier 1, tier 2, tier 3]
    solution: |
    seeded_bugs: [...]      # code the checker must reject
recap: [3 to 5 points]      # feeds the review deck
```

### 1.3 Exercise checking

| Exercise type | Language | How it checks |
|---|---|---|
| Multiple choice with reasoning | Any | Option key, plus per-option feedback |
| Ordering, architecture design | Any | Order or option set compared to the key. Design tasks use a rubric checklist you tick, with a model answer |
| Fill the gap | Any | Normalised token match against accepted answers |
| Write the function, refactor | pandas, NumPy, scikit-learn | Runs in Pyodide against hidden pytest-style assertions |
| Write the function, refactor | PySpark | Static checks through Python's `ast` module in Pyodide: required and forbidden calls, imports, names. No Spark runs in the browser |
| Write, spot the bug | SQL, T-SQL, KQL, DAX | Normalised text rules: required and forbidden patterns |
| Predict the output | Any | Exact or normalised match |

All code checkers live in one Python package, `checkers/`. The browser runs it in Pyodide. CI runs the same code in CPython to prove every reference solution passes, every seeded bug fails and every listed wrong answer triggers its feedback. One implementation, tested once.

Feedback flow: a specific message when the answer matches a known wrong answer, three hints on request, and the full solution unlocks after one attempt.

### 1.4 App engine

- Plain ES modules, no framework, no build step for the app. Hash routing (`#/A/A5/A5-L2`) works on GitHub Pages without server rewrites.
- Code editor: a `<textarea>` with monospace font, tab handling and line numbers. Heavy editors misbehave on iOS Safari.
- Pyodide loads on the first code exercise, not on page load. The service worker caches it for offline use after the first load.
- Progress in `localStorage` under one versioned key, with JSON export and import on the dashboard.
- Spaced repetition: SM-2 scheduling on recap cards. The dashboard shows today's queue.
- Engagement: XP per exercise (scaled by difficulty, reduced after hints), daily streak, badge per completed module, progress bar per track, mastery per module and per roadmap band.
- Track D7 answer keys stay hidden in the UI until you submit. They sit in the static bundle base64-encoded. This stops accidental reading, not a determined look at the source. That is enough for personal use.

### 1.5 PWA and iPhone

- `manifest.webmanifest` with `display: standalone`, icons at 180px (apple-touch-icon), 192px and 512px.
- Service worker: cache-first for the app shell and content, stale-while-revalidate for the content bundle, cache on first use for Pyodide.
- Layout tested at 390px width in Playwright (WebKit engine where available).
- Home-screen steps for Safari go in the README in Phase 6.

### 1.6 Handbook

- `scripts/build_handbook.py` loads the same YAML, renders Markdown to HTML, then:
  - PDF through WeasyPrint. A5 portrait for phone reading. Code blocks use `white-space: pre-wrap` with a hanging indent, so long lines wrap inside the block.
  - Word through python-docx. Code in a monospace style with shading.
- Three levels: full handbook, one track (4 files), one module (46 files), in both formats.
- Structure per module: concept summary, why it matters, weak versus strong code with annotations, recap card, practice exercises. Solutions and Track D answer keys go in a separate appendix. Contents page, roadmap tags on every module, one-page checklist per track.
- The build asserts every lesson in the bundle appears in the handbook. CI fails otherwise.

### 1.7 Notebooks and local practice

- `build_notebooks.py` writes one `.ipynb` per PySpark practical for Databricks Free Edition. Free Edition runs serverless compute only, so notebooks avoid features serverless lacks (to verify: `cache()`, classic Spark UI, RDD APIs).
- Fabric practicals become a notebook where Spark applies and a step-by-step lab (Markdown and PDF) for portal tasks.
- `practice/` holds a pytest harness: a session-scoped local SparkSession fixture with Delta configured, DataFrame equality helpers (`pyspark.testing.assertDataFrameEqual`), and one test module per PySpark practical. Needs Java 17 or 21 on your laptop.

### 1.8 Deployment

GitHub Actions: lint (ruff), type-check (mypy), content quality gates (pytest), build content, handbook and notebooks, then deploy `site/` to GitHub Pages. Generated downloads are also committed, as you asked.

## 2. Roadmap tagging

From `reference/roadmap.md`:

| Band | Tag | Modules |
|---|---|---|
| Prerequisite for all months | `prereq` | B1 to B14 |
| Months 1 to 3, PyTorch foundations | `M1-3` | B16 |
| Months 7 to 9, NLP with deep learning | `M7-9` | B15 |
| Months 16 to 18, MLOps and deployment, plus current work | `M16-18`, `current-work` | Track A, Track C |
| Every month | `all-months` | Track D |

Proposed additions for your decision:
- B14 (MLflow): `prereq` and `M16-18`, since the roadmap names MLflow tracking and registry in months 16 to 18.
- B17 (testing and performance): `prereq`. Your tagging rule does not cover it.
- B18 (documentation and communication): `prereq` and `all-months`, since the roadmap asks for monthly learning documentation.
- B12 (model evaluation): add `M4-6` and `M10-12` as secondary tags, since both bands list evaluation as a deliverable.

## 3. Syllabus

Every lesson has 5 or more exercises. Module count: 46. Lesson count: 138 plus 3 capstones.

### Track A: Databricks pipeline engineering (tags: M16-18, current-work)

| Module | Lesson 1 | Lesson 2 | Lesson 3 |
|---|---|---|---|
| A1 Code structure | Single-purpose functions and naming | Type hints and docstrings that a reviewer trusts | Config files over hardcoded values, and PEP 8 with ruff |
| A2 Medallion architecture | Bronze contract: append-only with audit columns | Silver contract: canonical names, types and grain | Gold contract: documented grain and aggregates for Power BI |
| A3 Delta Lake | Idempotent MERGE and deduplicating the source | Schema enforcement and schema evolution | Time travel, OPTIMIZE, VACUUM and table properties |
| A4 Unity Catalog | Three-level namespace and layer schemas | Grants to groups and least privilege | Row filters and column masks (SQL UDF plus SET ROW FILTER) |
| A5 PySpark performance | Lazy evaluation, actions and repeated counts | Built-in functions over Python UDFs | Joins, broadcast, partitioning, caching and reading explain plans |
| A6 Data quality | Data contracts with severity levels | Table health checks in one pass | Reconciliation between bronze, silver and gold |
| A7 Observability | Structured logging with the logging module | Pipeline run log table with an explicit schema | Alerting on failed runs and QA results |
| A8 Incremental processing | Processing only new waves correctly | Auto Loader for file ingestion | Change data feed for downstream layers |
| A9 Testing | pytest basics and fixtures for Spark | Local SparkSession and test data builders | DataFrame equality checks and testing MERGE logic |
| A10 Deployment | Git folders and branching | Databricks Asset Bundles and parameterised jobs | CI: lint, type-check and test on every pull request |

### Track B: Python for data science

| Module | Tags | Lesson 1 | Lesson 2 | Lesson 3 |
|---|---|---|---|---|
| B1 Project setup | prereq | pyproject.toml and folder layout | Virtual environments and dependency groups | ruff and mypy in daily work |
| B2 Code design | prereq | Pure functions and side effects at the edges | Dataclasses and configuration objects | When a class earns its place |
| B3 Clean pandas | prereq | Dtypes, including nullable and string dtypes in pandas 3 | Vectorisation over apply and loops | Method chaining and Copy-on-Write |
| B4 Polars and DuckDB | prereq | Polars expressions and lazy frames | DuckDB SQL over Parquet and DataFrames | Choosing pandas, Polars, DuckDB or Spark |
| B5 Data validation | prereq | Schema checks with pandera | Input models with pydantic | Validation at pipeline boundaries |
| B6 Reproducibility | prereq | Seeds and random state | Config files and data versioning | Pinned dependencies and lock files |
| B7 Exploratory analysis | prereq | Profiling a new dataset | Visual checks that catch data errors | Documenting assumptions |
| B8 Statistical correctness | prereq | Survey weights and weighted estimates | Confidence intervals and effect sizes | Multiple comparisons |
| B9 Experimental design | prereq | Power and sample size | Analysing an A/B test | Pitfalls: peeking, sample ratio mismatch, novelty effects |
| B10 Feature engineering | prereq | Target leakage | Train-test contamination through preprocessing | Time-based features without look-ahead |
| B11 ML workflow | prereq | Splits: random, stratified, grouped, time-based | Pipeline and ColumnTransformer | Cross-validation and hyperparameter search |
| B12 Model evaluation | prereq, M4-6, M10-12 | Choosing a metric for the decision | Calibration | Imbalanced classes and error analysis |
| B13 Interpretability and fairness | prereq | Permutation importance | SHAP values and their limits | Subgroup performance |
| B14 MLflow | prereq, M16-18 | Experiment tracking | Model registry and aliases | Reproducing a logged run |
| B15 Embeddings and clustering | M7-9 | Sentence embeddings with SentenceTransformers | Clustering with HDBSCAN | Validating clusters |
| B16 PyTorch hygiene | M1-3 | Device handling | A correct training loop (train and eval modes, zero_grad) | Reproducibility in PyTorch |
| B17 Testing and performance | prereq | Unit tests for data code | Property-based tests with Hypothesis | Profiling time and memory |
| B18 Documentation | prereq, all-months | Docstrings and READMEs | Model cards | Decision logs |

Pyodide note: B15 and B16 need SentenceTransformers, HDBSCAN and PyTorch, which Pyodide does not run. These lessons use static checks, prediction and spot-the-bug exercises, with notebooks for laptop practice.

### Track C: Microsoft Fabric (tags: M16-18, current-work)

| Module | Lesson 1 | Lesson 2 | Lesson 3 |
|---|---|---|---|
| C1 Fabric architecture | Tenants, capacities and workspaces | Items and experiences | OneLake as one logical lake |
| C2 Lakehouse, Warehouse, SQL endpoint | Lakehouse and its SQL analytics endpoint | Warehouse and T-SQL writes | Choosing between them |
| C3 Unifying datasets | OneLake shortcuts | Mirroring, including Azure Databricks Unity Catalog | Avoiding duplicate copies |
| C4 Ingestion and orchestration | Data Factory pipelines | Dataflows Gen2 | Copy jobs and choosing a tool |
| C5 Spark notebooks in Fabric | Differences from Databricks | Environments and library management | V-Order and Delta interoperability |
| C6 Semantic models and Direct Lake | Star schemas | Direct Lake and fallback behaviour | DAX best practices and filter context |
| C7 Real-Time Intelligence | Eventstream | Eventhouse and KQL | Activator |
| C8 Copilot and AI in Fabric | Copilot in notebooks and SQL | Copilot in Data Factory and Power BI | Fabric data agents, limits and verifying output |
| C9 Governance and security | Domains and workspace roles | OneLake security and sensitivity labels | Purview and lineage |
| C10 DevOps and cost | Git integration | Deployment pipelines | Capacity monitoring and cost control |

### Track D: Finding errors in code (tag: all-months)

| Module | Lesson 1 | Lesson 2 | Lesson 3 |
|---|---|---|---|
| D1 Reading errors | Python tracebacks, bottom up | Spark stack traces and the real cause | Py4J and Spark Connect errors |
| D2 Debugging tools | breakpoint() and pdb | Logging levels | Spark UI, query profile and explain() |
| D3 Silent errors | Join row explosion and nulls in filters | Type coercion and timezone drift | Mutable default arguments and truthiness of zero |
| D4 Data errors | Row counts across layers | Distribution drift | Weight totals and survey checks |
| D5 AI-generated code errors | Invented functions, parameters and syntax from other platforms | Deprecated APIs and version mismatches | Missing edge cases, self-confirming tests, secrets, over-engineering, wrong DAX filter context |
| D6 Verifying AI output | Read before running and check each API | Small data with a known answer, failing test first | Ask for assumptions and compare a second approach |
| D7 Review practice | 8 Python and pandas snippets | 9 PySpark and Spark SQL snippets | 8 SQL and DAX snippets |
| D8 Prompting for correct code | State versions and constraints | State expected outputs and tests | Iterate on a failing answer |

D7 holds 25 snippets across its three lessons. Grading counts bugs found and fixes proposed. The answer key stays hidden until you submit.

Your reference code seeds Track D. On top of the 12 defects in your README, I found these. I will verify the starred ones before use:

13. `log_pipeline_run` builds a DataFrame from a dict with `error_message=None`. Schema inference fails on a column where every value is null.
14. `upsert_silver` does not deduplicate the source. A redelivery with a repeated key fails the MERGE with a "multiple source rows matched" error.
15. `compute_gold_reach_metrics` promises "tracker x wave x subgroup grain" but does not group by `tracker_id`.
16. `sum(when(col("reach_flag") == 1, 1))` returns null, not 0, for a subgroup with no reach.
17. `_check_key_uniqueness` checks each key column on its own. A composite key needs one distinct count across all key columns.
18. `transform_to_silver`: `withColumnRenamed` does nothing when the source column is missing, so a renamed column in a delivery vanishes without error.
19. `check_weight_distribution` calls `round()` on `None` for an empty DataFrame and raises `TypeError`.
20. `ingest_to_bronze` counts, then writes, so it reads the source twice.
21. (*) `'owner'` is a reserved table property and fails in `SET TBLPROPERTIES`.
22. (*) `is_member()` checks workspace groups. Unity Catalog guidance favours `is_account_group_member()`.
23. (*) Under Spark 4.0 ANSI mode, a bad `cast` in `transform_to_silver` raises an error. Under older runtimes it returned null without warning.

### Capstones

| Capstone | Tags | Deliverable |
|---|---|---|
| 1. Refactor a messy notebook pipeline | M16-18, current-work | Refactored modules to the CLAUDE.md standard, pytest suite on a local SparkSession, run log and QA checks |
| 2. Unified Fabric solution | M16-18, current-work | Mirrored Databricks gold tables in OneLake, Direct Lake semantic model, Copilot-assisted report, verification log for every Copilot output |
| 3. Review an AI-generated pull request | all-months | Review report graded against a hidden key |

## 4. Decisions

Recorded on 25 September 2026:
- pandas 3.x for Track B.
- Roadmap tags as proposed in section 2, including the four additions. The month ranges stay as your roadmap file states them.
- Databricks Runtime 17.3 LTS (Spark 4.0) for lessons.
- PDF at A5 portrait for iPhone reading. The Word file uses A4 with a wide right margin for notes.

## 5. Original blockers and questions

1. Network access. This build environment blocks `learn.microsoft.com`, `docs.databricks.com` and `cdn.jsdelivr.net`. I verified versions through PyPI, npm and search results that quote official pages. To meet your accuracy rule and to test Pyodide, add these hosts to the environment's allowed domains: `learn.microsoft.com`, `docs.databricks.com`, `cdn.jsdelivr.net`, `pyodide.org`. You change this under Network access in the environment settings.
2. Roadmap tags. Confirm the four proposed additions in section 2. Your roadmap file also says the month ranges are a proposed split. Confirm them or send the originals.
3. Target runtime. I propose DBR 17.3 LTS (Spark 4.0) for lessons, with notes where 18 LTS differs. Switch if 18 LTS is already your production runtime.
4. pandas version. I propose pandas 3.x, with notes where 2.x behaves differently. Tell me if your work environment still runs pandas 2.x.
5. PDF page size. I propose A5 portrait for iPhone reading. A4 suits printing better.
