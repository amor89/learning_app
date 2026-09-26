# Learning app

A personal, offline-capable course with four tracks: Databricks pipeline engineering, Python for data science, Microsoft Fabric, and finding errors in code. It runs as a static site on GitHub Pages and installs on an iPhone home screen.

Status: Phase 5 complete. All four tracks are written: Track A (Databricks pipeline engineering) 30 lessons, Track B (Python for data science) 54, Track C (Microsoft Fabric) 30, checked against Microsoft Learn, and Track D (Finding errors in code) 24, with 25 seeded review snippets and a hidden answer key in D7.

## Layout

| Path | What it holds |
|---|---|
| `content/` | Lesson YAML. The only place lesson text lives. |
| `learnkit/` | Content schema, loader, renderers for the app bundle and the handbook |
| `checkers/` | Python exercise checkers. The browser runs them in Pyodide, the tests in CPython. |
| `site/` | The static app served by GitHub Pages, plus generated content and downloads |
| `scripts/` | Build scripts: content bundle, handbook (PDF and Word), practicals |
| `practice/` | Local pytest harness with a SparkSession and Delta Lake |
| `tests/` | Quality gates for every exercise, store unit tests, browser smoke test |
| `reference/` | Your pipeline code and roadmap |

## Add a lesson

1. Create `content/tracks/<track>/<module>/<lesson id>.yaml`. Copy a sample lesson for the shape.
2. Run `python scripts/build_all.py`. The build rejects a lesson that breaks the format: concept length, at least 5 exercises of 3 or more types, rising difficulty, 3 hints each, 3 to 5 recap cards.
3. Run the quality gates (below). Commit the YAML and the generated `site/` files.

The engine never changes when you add a lesson.

## Set up and run the checks

```bash
python -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install -e . --group dev
python scripts/build_all.py
ruff check . && ruff format --check . && mypy
pytest                                   # Python checkers: solutions pass, seeded bugs fail
node --test tests/app/checkers.test.mjs tests/app/store.test.mjs
```

WeasyPrint needs Pango. On macOS: `brew install pango`. On Ubuntu: `apt install libpango-1.0-0 libpangoft2-1.0-0`.

Run the app locally: `python -m http.server -d site 8000`, then open http://localhost:8000.

Browser exercises run on the package versions that Pyodide 314.0.7 ships, which are older than the `dev` pins. The CI `parity` job reruns `pytest` on those versions (see `.github/workflows/ci.yml` for the exact pins). To run it locally, create another virtual environment on Python 3.13 and install the same pins.

Some Track B lessons teach libraries that neither Pyodide nor the `dev` group includes: MLflow, shap (in `dev`, not in Pyodide), PyTorch and sentence-transformers. Their code exercises check structure only. Install them yourself to run the examples.

## Laptop practice with Spark

See `practice/README.md`. Short version: install Java 17 or 21, create a separate virtual environment, `pip install -e . --group spark`, then `pytest practice`. The Spark harness needs pandas 2.x, so it cannot share the `dev` environment, which uses pandas 3.

## Documents

- `CLAUDE.md`: coding and content standards
- `VERSIONS.md`: pinned versions and Fabric feature status
- `docs/phase0-proposal.md`: architecture, syllabus and decisions
