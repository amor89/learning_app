"""Reference solution for src/serve_lab/drift.py.

Read this only after your own version passes the tests.
"""

from __future__ import annotations

from typing import Literal

import numpy as np

EPS = 1e-4
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
    if bins < 2:
        raise ValueError(f"bins must be at least 2, got {bins}")
    if len(expected) == 0 or len(actual) == 0:
        raise ValueError("expected and actual must not be empty")
    inner = np.unique(np.quantile(expected, np.linspace(0, 1, bins + 1))[1:-1])
    n_bins = len(inner) + 1
    e = np.bincount(np.searchsorted(inner, expected, side="right"), minlength=n_bins) / len(
        expected
    )
    a = np.bincount(np.searchsorted(inner, actual, side="right"), minlength=n_bins) / len(actual)
    e, a = np.clip(e, EPS, None), np.clip(a, EPS, None)
    return float(np.sum((a - e) * np.log(a / e)))


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
    if value < 0 or not 0 < warn < alert:
        raise ValueError(f"need value >= 0 and 0 < warn < alert, got {value}, {warn}, {alert}")
    if value >= alert:
        return "alert"
    if value >= warn:
        return "warn"
    return "stable"
