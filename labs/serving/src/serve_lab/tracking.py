"""Log a training run to MLflow and return the logged model's URI."""

from __future__ import annotations

import mlflow
from sklearn.pipeline import Pipeline


def log_run(model: Pipeline, accuracy: float, params: dict[str, float | int]) -> str:
    """Log parameters, validation accuracy and the model in one run.

    Returns:
        The model URI to register, such as "models:/m-...".
    """
    with mlflow.start_run():
        mlflow.log_params(params)
        mlflow.log_metric("val_accuracy", accuracy)
        info = mlflow.sklearn.log_model(model, name="model", input_example=["late parcel"])
    return str(info.model_uri)
