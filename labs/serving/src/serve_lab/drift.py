"""Drift checks you write: the population stability index and its bands.

Each function raises NotImplementedError until you fill it in.
tests/test_drift_and_model.py says what each must do, and runs without MLflow or FastAPI.
"""

from __future__ import annotations

from typing import Literal

import numpy as np

EPS = 0.0001
DriftStatus = Literal["stable", "warn", "alert"]


def psi(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
    """Population stability index of actual against expected (lesson B27-L5).

    Bin edges are the quantiles of expected, so each bin holds about the same
    share of expected values. Shares below EPS are raised to EPS so the
    logarithm stays finite.

    Args:
        expected: Values from the reference period, such as the training data.
        actual: Values from the period to check.
        bins: Number of quantile bins, at least 2.

    Returns:
        sum((a - e) * ln(a / e)) over bins; 0 when the shares match.

    Raises:
        ValueError: If bins is below 2 or either array is empty.
    """
    raise NotImplementedError("psi")


def drift_status(value: float, warn: float = 0.1, alert: float = 0.25) -> DriftStatus:
    """Label a PSI value with the common rule-of-thumb bands.

    Args:
        value: A PSI value.
        warn: Lowest value that counts as a moderate shift.
        alert: Lowest value that counts as a large shift.

    Returns:
        "stable", "warn" or "alert".

    Raises:
        ValueError: If value is negative or warn is not below alert.
    """
    raise NotImplementedError("drift_status")
