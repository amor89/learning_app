# Serving lab (Track B, module B27)

Take a model from a training run to a container that answers HTTP requests, then check it for drift. You register versions in MLflow, point the `champion` alias at one, serve it with FastAPI, package it with Docker and measure drift with the population stability index.

## Set up

From this folder:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
```

Most tests fail with `NotImplementedError`. That is the starting point. The data is synthetic open survey answers about price, delivery or staff, built in code, so nothing downloads. The lab was checked with Python 3.12, MLflow 3.17.2, FastAPI 0.162.0, uvicorn 0.54.0 and scikit-learn 1.9.1.

## What is here

| Path | What it holds |
|---|---|
| `src/serve_lab/data.py` | Builds answers and topics. `shifted=True` builds a later, drifted batch. |
| `src/serve_lab/model.py` | Trains TF-IDF plus logistic regression; saves and loads the model file the container serves. Given. |
| `src/serve_lab/tracking.py` | Logs a run and its model to MLflow. Given. |
| `src/serve_lab/schemas.py` | Request and response schemas. Given. |
| `src/serve_lab/settings.py`, `app.py` | Settings from environment variables, and the app factory uvicorn calls. Given. |
| `src/serve_lab/drift.py` | You write: `psi` and `drift_status`. NumPy only. |
| `src/serve_lab/api.py` | You write: `create_app`, with `/health` and `/predict`. |
| `src/serve_lab/registry.py` | You write: `register`, `promote` and `load_alias`. |
| `Dockerfile`, `requirements-serve.txt` | The serving image and its pinned dependencies. |
| `tests/` | What each part must do. API and registry tests skip without FastAPI and MLflow. |
| `solution/` | Reference answers. Read them only after your tests pass. |

## Your task

1. Write `psi` and `drift_status` (lesson B27-L5). Run `pytest tests/test_drift_and_model.py`.
2. Write `register`, `promote` and `load_alias` (lesson B27-L1), then `create_app` (lesson B27-L2). Run `pytest`: every test passes.
3. Train and register two versions, promote one, and export it for the container:

   ```bash
   export MLFLOW_TRACKING_URI=sqlite:///mlflow.db     # Windows: set MLFLOW_TRACKING_URI=sqlite:///mlflow.db
   python -m serve_lab train                # version 1, validation accuracy 0.9760
   python -m serve_lab train --c 0.01       # version 2, validation accuracy 0.9700
   python -m serve_lab promote 1
   python -m serve_lab export               # writes model/
   python -m serve_lab serve                # http://127.0.0.1:8000/docs
   ```

4. Build and run the image (lesson B27-L3), then call it:

   ```bash
   docker build -t survey-topics:1 .
   docker run --rm -p 8000:8000 survey-topics:1
   curl -X POST localhost:8000/predict -H "content-type: application/json" -d '{"texts": ["the courier was late again"]}'
   ```

   The reference image answered `delivery` with confidence 0.972, ran as `appuser`, logged one JSON line per request without the texts, and was 561 MB.

5. Run `python -m serve_lab drift`. The reference report:

   | Feature | PSI | Status |
   |---|---|---|
   | Answer length, shifted batch | 4.708 | alert |
   | Confidence, shifted batch | 0.687 | alert |
   | Confidence, unshifted batch | 0.008 | stable |

6. Deploy the image to Azure Container Apps (lesson B27-L4) if you have a subscription, call `/health` and `/predict` on its URL, then delete the resource group.
7. Write your README: the registry steps, the API contract, the image, the deployment, the drift report, and how you would roll back (lesson B27-L6).

## Extend it

- Add a `/version` route that returns the model name, version and training accuracy.
- Log the drift report's PSI values to MLflow as metrics, one run per check.
- Promote version 2, export and rebuild the image, then roll back by promoting version 1 again.
