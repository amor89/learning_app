"""Reference solution for src/serve_lab/api.py.

Read this only after your own version passes the tests.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from serve_lab.model import ModelMeta
from serve_lab.schemas import Loader, Prediction, PredictRequest, PredictResponse

LOGGER = logging.getLogger("serve_lab.api")


def create_app(loader: Loader, max_batch: int = 100) -> FastAPI:
    """Build the API. The model loads once, at start-up (lesson B27-L2).

    Args:
        loader: Returns the model and its metadata. Tests pass a fake.
        max_batch: Most answers one request may hold.

    Returns:
        A FastAPI app with GET /health and POST /predict.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.model, app.state.meta = loader()
        yield

    app = FastAPI(title="Survey topics", lifespan=lifespan)

    @app.get("/health")
    def health() -> dict[str, str]:
        """200 with the model version once the model has loaded, else 503."""
        if getattr(app.state, "model", None) is None:
            raise HTTPException(status_code=503, detail="model not loaded")
        return {"status": "ok", "model_version": app.state.meta.version}

    @app.post("/predict", response_model=PredictResponse)
    def predict(request: PredictRequest) -> PredictResponse:
        """Topic and confidence for each answer. Logs one record per request, without the texts."""
        if len(request.texts) > max_batch:
            raise HTTPException(status_code=413, detail=f"at most {max_batch} texts per request")
        start = time.perf_counter()
        probs = app.state.model.predict_proba(request.texts)
        best = probs.argmax(axis=1)
        predictions = [
            Prediction(label=str(app.state.model.classes_[i]), confidence=round(float(row[i]), 4))
            for i, row in zip(best, probs, strict=True)
        ]
        meta: ModelMeta = app.state.meta
        record = {
            "event": "predict",
            "model_version": meta.version,
            "n_texts": len(predictions),
            "mean_confidence": round(float(probs.max(axis=1).mean()), 4),
            "latency_ms": round((time.perf_counter() - start) * 1_000, 2),
        }
        LOGGER.info(json.dumps(record))
        return PredictResponse(
            predictions=predictions, model_name=meta.name, model_version=meta.version
        )

    return app
