"""The model registry steps you write: register a version, point an alias, load by alias.

Each function raises NotImplementedError until you fill it in.
tests/test_registry.py says what each must do.
"""

from __future__ import annotations

from sklearn.pipeline import Pipeline

from serve_lab.model import ModelMeta


def register(model_uri: str, name: str) -> str:
    """Register a logged model as a new version (lesson B27-L1).

    Args:
        model_uri: The URI log_model returned, such as "models:/m-...".
        name: Registered model name.

    Returns:
        The new version number, as a string.
    """
    raise NotImplementedError("register")


def promote(name: str, version: str, alias: str = "champion") -> None:
    """Point an alias at a version. Rolling back is promoting the old version again.

    Raises:
        ValueError: If alias is empty or version is not a positive whole number.
    """
    raise NotImplementedError("promote")


def load_alias(name: str, alias: str = "champion") -> tuple[Pipeline, ModelMeta]:
    """Load the version an alias points to, and report that version.

    Resolves the alias once, then loads that exact version, so the model and
    the reported version agree even if someone moves the alias meanwhile.
    """
    raise NotImplementedError("load_alias")
