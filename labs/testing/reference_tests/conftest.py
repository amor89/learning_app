"""Shared fixtures for the reference test suite."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def rng() -> np.random.Generator:
    """A seeded generator, so random tests draw the same numbers every run."""
    return np.random.default_rng(7)


@pytest.fixture
def make_respondents() -> Callable[..., pd.DataFrame]:
    """Factory for small respondent frames with defaults for every column."""

    def make(weights: list[float], in_scope: list[bool] | None = None) -> pd.DataFrame:
        ids = [f"R{i}" for i in range(1, len(weights) + 1)]
        flags = in_scope if in_scope is not None else [True] * len(weights)
        return pd.DataFrame(
            {"respondent_id": ids, "final_weight": [float(w) for w in weights], "in_scope": flags}
        )

    return make
