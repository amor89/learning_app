"""Reference solution for src/serve_lab/registry.py.

Read this only after your own version passes the tests.
"""

from __future__ import annotations

import mlflow
from mlflow import MlflowClient
from serve_lab.model import ModelMeta
from sklearn.pipeline import Pipeline


def register(model_uri: str, name: str) -> str:
    """Register a logged model as a new version (lesson B27-L1).

    Args:
        model_uri: The URI log_model returned, such as "models:/m-...".
        name: Registered model name.

    Returns:
        The new version number, as a string.
    """
    return str(mlflow.register_model(model_uri, name).version)


def promote(name: str, version: str, alias: str = "champion") -> None:
    """Point an alias at a version. Rolling back is promoting the old version again.

    Raises:
        ValueError: If alias is empty or version is not a positive whole number.
    """
    if not alias or not version.isdigit() or int(version) < 1:
        raise ValueError(f"need an alias and a positive version, got {alias!r}, {version!r}")
    MlflowClient().set_registered_model_alias(name, alias, version)


def load_alias(name: str, alias: str = "champion") -> tuple[Pipeline, ModelMeta]:
    """Load the version an alias points to, and report that version.

    Resolves the alias once, then loads that exact version, so the model and
    the reported version agree even if someone moves the alias meanwhile.
    """
    version = MlflowClient().get_model_version_by_alias(name, alias).version
    model: Pipeline = mlflow.sklearn.load_model(f"models:/{name}/{version}")
    return model, ModelMeta(name=name, version=str(version))
