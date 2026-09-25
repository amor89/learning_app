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
| NumPy | 2.5.3 | 2.x | Verified (PyPI) |
| DuckDB | 1.5.5 | 1.5.x | Verified (PyPI) |
| pandera | 0.33.1 | 0.33.x | Verified (PyPI) |
| pydantic | 2.13.5 | 2.x | Verified (PyPI) |
| PySpark (local harness) | 4.2.0 latest. 4.0.4 matches DBR 17.3 LTS | 4.0.4 | Verified (PyPI) |
| delta-spark (local harness) | 4.4.0 latest. 4.0.1 pairs with Spark 4.0 | 4.0.1 | Verified (PyPI). Pairing with Spark 4.0 unverified against the Delta compatibility table |
| ruff | 0.16.9 | 0.16.x | Verified (PyPI) |
| mypy | 2.3.1 | 2.3.x | Verified (PyPI) |
| pytest | 9.1.1 | 9.x | Verified (PyPI) |
| python-docx | 1.2.0 | 1.2.x | Verified (PyPI) |
| WeasyPrint (PDF build) | 70.0 | 70.x | Verified (PyPI) |

## Browser runtime

| Item | Version | Status | Notes |
|---|---|---|---|
| Pyodide | 314.0.7 | Verified (npm registry) | The versions of pandas, NumPy and scikit-learn bundled with this release are unverified. The Pyodide CDN (cdn.jsdelivr.net) is blocked in this build environment. Browser exercises must state the Pyodide package versions, which differ from the laptop pins above. |

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
- Spark 4.0 turns ANSI mode on by default, so an invalid `cast` raises an error instead of returning null. Unverified for DBR 17.3 LTS. Affects A2 and D3.
