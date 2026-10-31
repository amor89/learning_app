"""Survey weight helpers."""

from __future__ import annotations

import pandas as pd

MIN_CAP = 1.0


def normalise(weights: list[float]) -> list[float]:
    """Scale weights so they sum to 1.

    Args:
        weights: Non-negative weights.

    Returns:
        The weights divided by their total.

    Raises:
        ValueError: If a weight is negative or the weights sum to 0.
    """
    for i, w in enumerate(weights):
        if w < 0:
            raise ValueError(f"negative weight at index {i}")
    total = sum(weights)
    if total == 0:
        raise ValueError("total weight is 0")
    return [w / total for w in weights]


def cap_weights(df: pd.DataFrame, cap: float) -> pd.DataFrame:
    """Return a copy of df with final_weight capped at cap.

    Args:
        df: Respondents with a final_weight column.
        cap: Largest weight allowed, at least 1.

    Returns:
        A new frame. Missing weights stay missing.

    Raises:
        ValueError: If cap is below 1.
    """
    if cap < MIN_CAP:
        raise ValueError(f"cap must be at least {MIN_CAP}, got {cap}")
    return df.assign(final_weight=df["final_weight"].clip(upper=cap))


def in_scope_weight(df: pd.DataFrame) -> float:
    """Total final_weight of rows where in_scope is true."""
    return float(df.loc[df["in_scope"], "final_weight"].sum())


def effective_n(weights: list[float]) -> float | None:
    """Kish's effective sample size, (sum w)^2 / sum w^2.

    Returns:
        The effective sample size, or None when the sum of squared weights is 0.
    """
    squares = sum(w * w for w in weights)
    if squares == 0:
        return None
    return sum(weights) ** 2 / squares
