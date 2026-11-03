"""Preprocessing and early stopping: the NumPy steps you write.

Each function and method raises NotImplementedError until you fill it in.
tests/test_prep.py says what each must do. None of this needs PyTorch.
"""

from __future__ import annotations

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
    raise NotImplementedError("split_indices")


class Standardiser:
    """Scales features with statistics fitted on training rows only (lesson B10-L2)."""

    mean: np.ndarray | None
    std: np.ndarray | None

    def __init__(self) -> None:
        """Start unfitted."""
        raise NotImplementedError("Standardiser.__init__")

    def fit(self, X: np.ndarray) -> Standardiser:
        """Learn each column's mean and standard deviation.

        Args:
            X: Training features, shape (n, k).

        Returns:
            The fitted standardiser.

        Raises:
            ValueError: If X has no rows or holds NaN.
        """
        raise NotImplementedError("Standardiser.fit")

    def transform(self, X: np.ndarray) -> np.ndarray:
        """Scale rows with the fitted statistics.

        Raises:
            RuntimeError: If fit has not been called.
        """
        raise NotImplementedError("Standardiser.transform")


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
        raise NotImplementedError("EarlyStopping.__init__")

    def step(self, val_loss: float, state: dict[str, Any]) -> bool:
        """Record one epoch's validation loss and model state.

        Args:
            val_loss: This epoch's validation loss.
            state: The model's state_dict(). A deep copy is kept when it is the best.

        Returns:
            True when training should stop.
        """
        raise NotImplementedError("EarlyStopping.step")
