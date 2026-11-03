"""App factory for uvicorn: `uvicorn serve_lab.app:build --factory`.

Nothing loads at import time. Settings are read and checked when uvicorn
calls build().
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

from serve_lab.api import create_app
from serve_lab.model import load_artifact
from serve_lab.settings import Settings


def build() -> FastAPI:
    """Read settings from the environment and build the app around the saved model.

    Sends INFO records, such as the one-line JSON per prediction, to standard
    error, where the container platform collects them.
    """
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    settings = Settings.from_env()
    return create_app(lambda: load_artifact(settings.model_dir), settings.max_batch)
