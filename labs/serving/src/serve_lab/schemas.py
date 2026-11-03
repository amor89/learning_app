"""Request and response schemas, and what the API needs from a model (lesson B27-L2)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any, Protocol

import numpy as np
from pydantic import BaseModel, Field

from serve_lab.model import ModelMeta


class Predictor(Protocol):
    """Anything with scikit-learn's predict_proba and classes_."""

    classes_: Any

    def predict_proba(self, texts: list[str]) -> np.ndarray:
        """Class probabilities, one row per text."""
        ...


Loader = Callable[[], tuple[Predictor, ModelMeta]]


class PredictRequest(BaseModel):
    """One to many answers, each 1 to 2,000 characters."""

    texts: list[Annotated[str, Field(min_length=1, max_length=2_000)]] = Field(min_length=1)


class Prediction(BaseModel):
    """The predicted topic of one answer and the model's probability for it."""

    label: str
    confidence: float


class PredictResponse(BaseModel):
    """Predictions in request order, and which model made them."""

    predictions: list[Prediction]
    model_name: str
    model_version: str
