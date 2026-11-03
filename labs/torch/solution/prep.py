"""Reference solutions for src/survey_torch/prep.py.

Read this only after your own version passes the tests. The repository's CI
copies this file over the stubs and runs the lab's tests.
"""

from __future__ import annotations

import copy
import math
from typing import Any

import numpy as np


def split_indices(
    n: int, val_share: float, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    """Shuffled training and validation row indices (lesson B23-L6).

    Args:
        n: Number of rows.
        val_share: Share of rows for validation, between 0 and 1.
        rng: Seeded generator.

    Returns:
        Training indices, then validation indices. The validation rows are the
        first round(n * val_share) of one permutation.

    Raises:
        ValueError: If val_share is not between 0 and 1, or either part is empty.
    """
    if not 0 < val_share < 1:
        raise ValueError(f"val_share must be between 0 and 1, got {val_share}")
    n_val = round(n * val_share)
    if n_val < 1 or n_val >= n:
        raise ValueError(f"{n} rows cannot give non-empty training and validation parts")
    order = rng.permutation(n)
    return order[n_val:], order[:n_val]


class Standardiser:
    """Scales features with statistics fitted on training rows only (lesson B10-L2)."""

    mean: np.ndarray | None
    std: np.ndarray | None

    def __init__(self) -> None:
        """Start unfitted."""
        self.mean: np.ndarray | None = None
        self.std: np.ndarray | None = None

    def fit(self, X: np.ndarray) -> Standardiser:
        """Learn each column's mean and standard deviation.

        Args:
            X: Training features, shape (n, k).

        Returns:
            The fitted standardiser.

        Raises:
            ValueError: If X has no rows or holds NaN.
        """
        if len(X) == 0 or np.isnan(X).any():
            raise ValueError("impute missing values first, and pass at least one row")
        std = X.std(axis=0)
        self.mean = X.mean(axis=0)
        self.std = np.where(std == 0, 1.0, std)
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        """Scale rows with the fitted statistics.

        Raises:
            RuntimeError: If fit has not been called.
        """
        if self.mean is None or self.std is None:
            raise RuntimeError("call fit on training rows first")
        result: np.ndarray = (X - self.mean) / self.std
        return result


class EarlyStopping:
    """Stops training when validation loss stops improving (lesson B16-L2)."""

    patience: int
    min_delta: float
    best_loss: float
    best_state: dict[str, Any] | None
    bad_epochs: int

    def __init__(self, patience: int, min_delta: float = 0.0) -> None:
        """Set the stopping rule.

        Args:
            patience: Epochs without improvement before stopping.
            min_delta: Smallest fall in loss that counts as an improvement.

        Raises:
            ValueError: If patience is below 1 or min_delta is negative.
        """
        if patience < 1 or min_delta < 0:
            raise ValueError(f"need patience >= 1 and min_delta >= 0, got {patience}, {min_delta}")
        self.patience = patience
        self.min_delta = min_delta
        self.best_loss = math.inf
        self.best_state: dict[str, Any] | None = None
        self.bad_epochs = 0

    def step(self, val_loss: float, state: dict[str, Any]) -> bool:
        """Record one epoch's validation loss and model state.

        Args:
            val_loss: This epoch's validation loss.
            state: The model's state_dict(). A deep copy is kept when it is the best.

        Returns:
            True when training should stop.
        """
        if val_loss < self.best_loss - self.min_delta:
            self.best_loss = val_loss
            self.best_state = copy.deepcopy(state)
            self.bad_epochs = 0
        else:
            self.bad_epochs += 1
        return self.bad_epochs >= self.patience
