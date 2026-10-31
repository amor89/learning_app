# Testing lab (Track B, module B19)

Build a full test suite for a small survey package, using everything from module B19.

## Set up

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e . --group dev
cd labs/testing
pytest
```

One example test passes. That shows pytest finds the package in `src/`.

## What is here

| Path | What it holds |
|---|---|
| `src/survey_stats/` | The code under test: age bands, weights, a Wilson interval and an API client. |
| `tests/` | Your tests. Start here. |
| `reference_tests/` | A complete suite with 100% branch coverage. Read it only after you finish. |
| `pyproject.toml` | pytest settings: `testpaths`, `pythonpath`, `--strict-markers` and the `slow` marker. |

## Your task

Follow the steps on the lab sheet for lesson B19-L8. When you finish, run:

```bash
pytest --cov=survey_stats --cov-branch --cov-report=term-missing
```

The Missing column should be empty. Then compare your suite with `pytest reference_tests`.
