# Learning app

A personal, offline-capable course with four tracks: Databricks pipeline engineering, Python for data science, Microsoft Fabric, and finding errors in code. It runs as a static site on GitHub Pages and installs on an iPhone home screen.

Status: Phase 6 complete. All four tracks and three capstones are written: Track A (Databricks pipeline engineering) 30 lessons, Track B (Python for data science) 54, Track C (Microsoft Fabric) 30, checked against Microsoft Learn, Track D (Finding errors in code) 24, and the Capstones track with 3 projects.

## Install on your iPhone

1. Open the site in **Safari**.
2. Tap the **Share** button, then **Add to Home Screen**, then **Add**.
3. Open the app from the Home Screen icon. It runs full screen.
4. While online, run one Python exercise, and open the lessons you want offline. The app caches its shell on first launch, each lesson when you open it, and Pyodide with each Python package the first time an exercise needs it.

Your progress lives in Safari's storage on the phone. Export it from **Settings** in the app before you clear Safari data or change phone, and import it on the new device.

The automated layout tests run in Chromium at 390px. Check a few lessons on the phone itself after each release: code blocks wrap, exercise buttons are reachable, and a Python exercise runs.

## Deploy to GitHub Pages

The `deploy` job in `.github/workflows/ci.yml` publishes `site/` after every gate passes on `main`.

1. In the repository, open **Settings > Pages** and set **Source** to **GitHub Actions**. Do this once.
2. Merge your branch into `main`. The site appears at `https://<user>.github.io/<repository>/`.

## Capstones

| Capstone | Where | Checked by |
|---|---|---|
| 1. Refactor a messy pipeline | `practice/capstone/before_pipeline.py` to `practice/exercises/x1_pipeline.py` | 11 acceptance tests: `pytest practice/tests/test_x1_pipeline.py` |
| 2. Unified Fabric solution | Lesson X2-L1 and its lab sheet | Your verification log, checked by the exercise 4 function, and the design note |
| 3. Review an AI-generated pull request | `practice/capstone/pr_review/PR.md` and lesson X3-L1 | A hidden answer key in the app |

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
