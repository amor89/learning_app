"""The PyTorch steps you write: dataset, model, one training epoch, evaluation.

Each function and method raises NotImplementedError until you fill it in.
tests/test_nn_steps.py says what each must do.
"""

from __future__ import annotations

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset


class SurveyRows(Dataset[tuple[torch.Tensor, torch.Tensor]]):
    """Rows of features and a 0/1 target as float32 tensors (lesson B23-L6)."""

    def __init__(self, X: np.ndarray, y: np.ndarray) -> None:
        """Convert once, at the edge.

        Raises:
            ValueError: If X and y have different numbers of rows.
        """
        raise NotImplementedError("SurveyRows.__init__")

    def __len__(self) -> int:
        """Number of rows."""
        raise NotImplementedError("SurveyRows.__len__")

    def __getitem__(self, i: int) -> tuple[torch.Tensor, torch.Tensor]:
        """Row i as (features, target)."""
        raise NotImplementedError("SurveyRows.__getitem__")


def make_model(n_features: int, hidden: int) -> nn.Module:
    """Linear, ReLU, Linear with one logit out (lessons B23-L4 and B23-L5).

    Raises:
        ValueError: If n_features or hidden is below 1.
    """
    raise NotImplementedError("make_model")


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader[tuple[torch.Tensor, torch.Tensor]],
    loss_fn: nn.Module,
    optimizer: torch.optim.Optimizer,
) -> float:
    """One pass over the training batches (lessons B23-L3 and B16-L2).

    Returns:
        The mean training loss per row.

    Raises:
        ValueError: If the loader yields no rows.
    """
    raise NotImplementedError("train_one_epoch")


def evaluate(
    model: nn.Module, loader: DataLoader[tuple[torch.Tensor, torch.Tensor]], loss_fn: nn.Module
) -> tuple[float, float]:
    """Mean loss and accuracy at a 0.5 threshold, in eval mode (lesson B16-L2).

    Returns:
        Mean loss per row, and the share of rows classified correctly.

    Raises:
        ValueError: If the loader yields no rows.
    """
    raise NotImplementedError("evaluate")
