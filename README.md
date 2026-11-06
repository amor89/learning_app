# Learning app

A personal, offline-capable course with four tracks: Databricks pipeline engineering, Python for data science, Microsoft Fabric, and finding errors in code. It runs as a static site on GitHub Pages and installs on an iPhone home screen.

Status: Phase 6 complete. All four tracks and three capstones are written: Track A (Databricks pipeline engineering) 33 lessons, Track B (Python for data science) 104, including PyTorch foundations for roadmap months 1 to 3, convolutional networks for months 4 to 6, attention and transformers from scratch for months 7 to 9, fine-tuning for months 10 to 12, prompting, RAG and LLM evaluation for months 13 to 15, and serving and monitoring for months 16 to 18, Track C (Microsoft Fabric) 33, checked against Microsoft Learn, Track D (Finding errors in code) 26, and the Capstones track with 3 projects.

## Pathways

The **Paths** tab lists four routes through the modules: the Senior Data Scientist roadmap, Databricks pipeline engineer, Microsoft Fabric, and Finding errors in code. Each pathway splits into stages, and each stage lists its modules and lessons with your progress, so you reach any lesson in two taps. Choose one with **Make this my pathway**: the dashboard's **Continue** button, its stage list and the **Next in your pathway** card at the end of each lesson then follow it. Tracks, module mastery and the handbook downloads sit under **All tracks, mastery and handbook downloads** on the dashboard.

`content/pathways.yaml` defines the pathways. The build rejects a pathway that names a missing module, lists a module twice, or leaves any module out of every pathway.

## Cheat sheets

Every module and every pathway stage has a cheat sheet: an A5 PDF with each lesson's takeaway, the code from its concept section and its recap cards. Open one from a module page, from the top of any lesson, from each stage of a pathway, or from the list on the library page. The sheet opens inside the app, with **Back** and the tab bar on screen. **Save PDF** opens the share sheet on an iPhone (choose **Save to Files**, then keep the PDF open in Files or Books beside your work) and downloads the file on a computer. The service worker keeps each sheet you open for offline use.

The app never links straight to a file. In an iPhone home-screen app, a PDF opened from a link replaces the app and leaves no way back, so the handbook, practical and cheat-sheet downloads all go through the same save button.

`scripts/build_cheatsheets.py` builds the PDFs into `site/downloads/cheatsheets/`, and `scripts/build_content.py` writes the same points for the in-app view to `site/content/sheets/`. Both read the lesson files, so the sheets never hold text of their own. `python scripts/build_all.py` runs it after the handbook.

## Placement quizzes

Each track with a start-here module (A0, B0, C0 and D0) has a ten-question placement quiz on it. Score 8 or more and the app offers to skip that module. Skipping takes it out of your route: **Continue** on the dashboard passes over it, and the pathway marks it **Skipped**. Score less and the result lists the start-here lessons behind the questions you missed. You can undo a skip or retake the quiz at any time, and a retake clears an earlier skip until you choose again.

The dashboard offers the quiz when **Continue** points into a start-here module you have not been placed on. The track page and the start-here module page offer it too, and show your last result.

The questions live in `content/placement/<track>.yaml`. Each names the start-here lessons that teach it. The loader rejects a quiz whose module is not the first of its track, or a question that names a lesson outside that module. `tests/content/test_placement.py` checks that every start-here module has a quiz and that each of its lessons has at least two questions. `scripts/build_content.py` writes `site/content/placement.json`.

## Interview practice

The **Interview** tab holds timed practice for senior data science interviews, the "running throughout" strand of `reference/roadmap.md`.

- **Theory drill.** Pick a topic and a length of 5, 10 or 20 questions. Each question has its own countdown, from 45 seconds to 2 minutes. Multiple-choice answers are marked for you. For an open question, answer aloud or jot notes, open the model answer, then tick the key points you covered: your score is the share you ticked. When the clock runs out, the answer locks and the model answer shows. Questions you have not seen come first, then those you scored lowest on. The bank holds 62 questions in 11 topics, from statistics to MLOps.
- **Build it from scratch.** Six tasks with a time limit of 10 to 30 minutes: a stratified train/test split, logistic regression by gradient descent, k-means, scaled dot-product attention with masks, cross-entropy from logits, and layer norm. You write NumPy only. The checker runs hidden tests in your browser through Pyodide, as lesson exercises do. The clock starts when you tap **Start the clock**, keeps running if you leave or reload, and stops at the first pass. The best time counts only runs where the solution stayed hidden, and it records the hints and the algorithm reminder you used. Once the task ends, interviewers' follow-up questions appear with model answers.

Every question and task names the lessons that teach it, and links back to them. Progress lives with the rest of your progress, so export and import include it.

The bank lives in `content/interview/`: `index.yaml` sets the topic and task order, `theory/<topic>.yaml` holds the questions and `tasks/<id>.yaml` holds each task. `scripts/build_content.py` writes `site/content/interview.json`. `tests/content/test_interview.py` checks that each reference solution passes, the starter and every seeded bug fail, each listed wrong answer hits its rule, solutions use only names a lesson or the task's primer explains, and every named lesson exists.

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
| `content/` | Lesson YAML, the only place lesson text lives, plus pathways and the interview practice bank |
| `learnkit/` | Content schema, loader, renderers for the app bundle and the handbook |
| `checkers/` | Python exercise checkers. The browser runs them in Pyodide, the tests in CPython. |
| `site/` | The static app served by GitHub Pages, plus generated content and downloads |
| `scripts/` | Build scripts: content bundle, handbook (PDF and Word), practicals |
| `practice/` | Local pytest harness with a SparkSession and Delta Lake |
| `labs/testing/` | The B19 testing lab: a small package to test, and a reference suite with 100% branch coverage |
| `labs/rag/` | The B21 RAG lab: methodology notes, 12 gold questions, a pipeline with seven functions to write, and a reference solution |
| `labs/torch/` | The B23 PyTorch lab: synthetic survey data, preprocessing and training steps to write, a logistic regression baseline, and a reference solution |
| `labs/cnn/` | The B24 CNN lab: scikit-learn's bundled digits, image and evaluation steps and a CNN to write, a dense network to compare with, and a reference solution |
| `labs/transformer/` | The B25 transformer lab: attention, multi-head self-attention, sinusoidal positions, a pre-norm block and a classifier to write, a synthetic task that needs token order, and a reference solution |
| `labs/finetune/` | The B26 fine-tuning lab: masked-token pretraining, then weight loading, freezing, a warm-up schedule and LoRA to write, a comparison of four strategies on 60 labels, and a reference solution |
| `labs/serving/` | The B27 serving lab: an MLflow registry with aliases, a FastAPI service, a Dockerfile, PSI drift checks to write, and a reference solution |
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
node --test tests/app/checkers.test.mjs tests/app/store.test.mjs tests/app/pathways.test.mjs tests/app/interview.test.mjs tests/app/placement.test.mjs
```

WeasyPrint needs Pango. On macOS: `brew install pango`. On Ubuntu: `apt install libpango-1.0-0 libpangoft2-1.0-0`.

Run the app locally: `python -m http.server -d site 8000`, then open http://localhost:8000.

Browser exercises run on the package versions that Pyodide 314.0.7 ships, which are older than the `dev` pins. The CI `parity` job reruns `pytest` on those versions (see `.github/workflows/ci.yml` for the exact pins). To run it locally, create another virtual environment on Python 3.13 and install the same pins.

Some Track B lessons teach libraries that neither Pyodide nor the `dev` group includes: MLflow, shap (in `dev`, not in Pyodide), PyTorch, sentence-transformers, Hugging Face transformers, peft, FastAPI and the MLflow registry. Their code exercises check structure only, or run the same idea in NumPy, as module B23 does for PyTorch. Install them yourself to run the examples.

## Laptop practice with Spark

See `practice/README.md`. Short version: install Java 17 or 21, create a separate virtual environment, `pip install -e . --group spark`, then `pytest practice`. The Spark harness needs pandas 2.x, so it cannot share the `dev` environment, which uses pandas 3.

## Testing lab

Module B19 ends with a laptop lab in `labs/testing/`. Use the `dev` environment, `cd labs/testing`, then `pytest`. Write your tests in `labs/testing/tests/`, measure them with `pytest --cov=survey_stats --cov-branch --cov-report=term-missing`, and compare with `reference_tests/`. See `labs/testing/README.md`.

## RAG lab

Module B21 ends with a laptop lab in `labs/rag/`: a retrieval-augmented generation pipeline over survey methodology notes. `cd labs/rag`, `pip install -e .`, then `pytest`. Fill in the seven functions in `src/survey_rag/steps.py` until the tests pass, then score retrieval with `python -m survey_rag eval`. A live model call is optional (`pip install -e ".[llm]"` and an Anthropic API key). See `labs/rag/README.md`.

## PyTorch lab

Module B23 ends with a laptop lab in `labs/torch/`: a small network on synthetic survey data, compared with logistic regression. `cd labs/torch`, `pip install -e .` (this installs PyTorch), then `pytest`. Fill in `src/survey_torch/prep.py` and `src/survey_torch/nn_steps.py` until the tests pass, then run `python -m survey_torch train`. The `dev` group has no PyTorch, so CI runs the lab's NumPy tests and skips the PyTorch ones. See `labs/torch/README.md`.

## CNN lab

Module B24 ends with a laptop lab in `labs/cnn/`: a small CNN on scikit-learn's bundled 8 by 8 digits, compared with a dense network. `cd labs/cnn`, `pip install -e .`, then `pytest`. Fill in `src/digits_cnn/vision.py` and `src/digits_cnn/models.py`, then run `python -m digits_cnn train`. As with the PyTorch lab, CI runs the NumPy tests and skips the PyTorch ones. See `labs/cnn/README.md`.

## Transformer lab

Module B25 ends with a laptop lab in `labs/transformer/`: a small transformer built from scratch on a synthetic task, does a sequence start and end with the same token? `cd labs/transformer`, `pip install -e .`, then `pytest`. Fill in `src/tiny_transformer/layers.py` and `src/tiny_transformer/model.py`, then run `python -m tiny_transformer train` with and without `--no-positions`. The tests check your attention against PyTorch's `scaled_dot_product_attention`. See `labs/transformer/README.md`.

## Fine-tuning lab

Module B26 ends with a laptop lab in `labs/finetune/`: pretrain a small transformer on unlabelled sequences, then fine-tune it on 60 labels from scratch, with a frozen encoder, fully and with LoRA. `cd labs/finetune`, `pip install -e .`, then `pytest`. Fill in `schedule.py`, `strategies.py` and `lora.py` in `src/finetune_lab/`, then run `python -m finetune_lab pretrain` and `python -m finetune_lab compare`. See `labs/finetune/README.md`.

## Serving lab

Module B27 ends with a laptop lab in `labs/serving/`: register a survey-topic classifier in MLflow, serve the `champion` alias with FastAPI, build a Docker image and check drift with PSI. `cd labs/serving`, `pip install -e ".[dev]"`, then `pytest`. Fill in `drift.py`, `registry.py` and `api.py` in `src/serve_lab/`, then follow `labs/serving/README.md`. CI runs the drift and model tests and skips the MLflow and FastAPI ones.

## Documents

- `CLAUDE.md`: coding and content standards
- `VERSIONS.md`: pinned versions and Fabric feature status
- `docs/phase0-proposal.md`: architecture, syllabus and decisions
