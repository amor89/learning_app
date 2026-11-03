"""The API you write: a health route and a prediction route around a model.

create_app raises NotImplementedError until you fill it in. The schemas are
given in schemas.py. tests/test_api.py says what the app must do.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

from serve_lab.schemas import Loader

LOGGER = logging.getLogger("serve_lab.api")


def create_app(loader: Loader, max_batch: int = 100) -> FastAPI:
    """Build the API. The model loads once, at start-up (lesson B27-L2).

    Args:
        loader: Returns the model and its metadata. Tests pass a fake.
        max_batch: Most answers one request may hold.

    Returns:
        A FastAPI app with GET /health and POST /predict.
    """
    raise NotImplementedError("create_app")
