"""What api.py must do. Skipped without FastAPI and httpx."""

from __future__ import annotations

import json
import logging

import numpy as np
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient
from serve_lab.api import create_app
from serve_lab.model import ModelMeta


class FakeModel:
    """Two classes; 'late' anywhere in a text means delivery."""

    classes_ = np.array(["delivery", "price"])

    def predict_proba(self, texts: list[str]) -> np.ndarray:
        return np.array([[0.9, 0.1] if "late" in t else [0.2, 0.8] for t in texts])


@pytest.fixture
def calls() -> list[int]:
    return []


@pytest.fixture
def client(calls: list[int]) -> TestClient:
    def loader() -> tuple[FakeModel, ModelMeta]:
        calls.append(1)
        return FakeModel(), ModelMeta("survey_topics", "7")

    with TestClient(create_app(loader, max_batch=3)) as test_client:
        yield test_client


def test_health_reports_the_version(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "model_version": "7"}


def test_health_is_503_before_start_up() -> None:
    app = create_app(lambda: (FakeModel(), ModelMeta("m", "1")))
    response = TestClient(app).get("/health")
    assert response.status_code == 503


def test_predict(client: TestClient) -> None:
    response = client.post("/predict", json={"texts": ["parcel was late", "too expensive"]})
    assert response.status_code == 200
    body = response.json()
    assert body["model_name"] == "survey_topics" and body["model_version"] == "7"
    assert body["predictions"] == [
        {"label": "delivery", "confidence": 0.9},
        {"label": "price", "confidence": 0.8},
    ]


@pytest.mark.parametrize(
    "payload", [{"texts": []}, {"texts": [""]}, {"text": ["late"]}, {"texts": "late"}]
)
def test_bad_requests_are_422(client: TestClient, payload: dict[str, object]) -> None:
    assert client.post("/predict", json=payload).status_code == 422


def test_too_many_texts_is_413(client: TestClient) -> None:
    assert client.post("/predict", json={"texts": ["a", "b", "c", "d"]}).status_code == 413


def test_model_loads_once(client: TestClient, calls: list[int]) -> None:
    for _ in range(3):
        client.post("/predict", json={"texts": ["late"]})
    assert len(calls) == 1


def test_logs_one_record_without_texts(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="serve_lab.api"):
        client.post("/predict", json={"texts": ["my parcel was late", "too expensive"]})
    records = [json.loads(r.getMessage()) for r in caplog.records if r.name == "serve_lab.api"]
    assert len(records) == 1
    record = records[0]
    assert (
        record["event"] == "predict" and record["model_version"] == "7" and record["n_texts"] == 2
    )
    assert record["mean_confidence"] == pytest.approx(0.85) and record["latency_ms"] >= 0
    assert "parcel" not in json.dumps(record)
