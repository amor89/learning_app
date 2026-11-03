"""What registry.py must do, and the whole path from training to a served prediction.

Skipped without MLflow, FastAPI and httpx.
"""

from __future__ import annotations

from pathlib import Path

import pytest

mlflow = pytest.importorskip("mlflow")
pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from serve_lab.__main__ import drift_report  # noqa: E402
from serve_lab.app import build  # noqa: E402
from serve_lab.model import save_artifact, train  # noqa: E402
from serve_lab.registry import load_alias, promote, register  # noqa: E402
from serve_lab.tracking import log_run  # noqa: E402

NAME = "survey_topics"


@pytest.fixture(autouse=True)
def tracking(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    uri = f"sqlite:///{tmp_path / 'mlflow.db'}"
    monkeypatch.setenv("MLFLOW_TRACKING_URI", uri)
    monkeypatch.setenv("MLFLOW_DISABLE_AGENT_HINT", "1")
    mlflow.set_tracking_uri(uri)


def _two_versions() -> None:
    for c in (1.0, 0.01):
        model, accuracy = train(n_train=300, n_val=100, c=c)
        register(log_run(model, accuracy, {"C": c}), NAME)


def test_register_promote_load_and_roll_back() -> None:
    _two_versions()
    promote(NAME, "2")
    _, meta = load_alias(NAME)
    assert meta.version == "2"
    promote(NAME, "1")
    model, meta = load_alias(NAME)
    assert meta.version == "1" and meta.name == NAME
    assert list(model.predict(["parcel was late"])) == ["delivery"]


def test_promote_guards() -> None:
    with pytest.raises(ValueError):
        promote(NAME, "0")
    with pytest.raises(ValueError):
        promote(NAME, "1", alias="")


def test_served_prediction_end_to_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _two_versions()
    promote(NAME, "1")
    model, meta = load_alias(NAME)
    save_artifact(model, meta, tmp_path / "model")
    monkeypatch.setenv("MODEL_DIR", str(tmp_path / "model"))
    with TestClient(build()) as client:
        body = client.post("/predict", json={"texts": ["the courier was late"]}).json()
    assert body["model_version"] == "1" and body["predictions"][0]["label"] == "delivery"


def test_drift_report_flags_the_shifted_batch() -> None:
    rows = {name: status for name, _, status in drift_report(1_000, seed=0)}
    assert rows["answer_length"] == "alert"
    assert rows["confidence, unshifted batch"] == "stable"
