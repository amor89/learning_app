"""Reference solutions for src/survey_torch/nn_steps.py.

Read this only after your own version passes the tests.
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
        if len(X) != len(y):
            raise ValueError(f"X has {len(X)} rows and y has {len(y)}")
        self.X = torch.as_tensor(X, dtype=torch.float32)
        self.y = torch.as_tensor(y, dtype=torch.float32)

    def __len__(self) -> int:
        """Number of rows."""
        return len(self.y)

    def __getitem__(self, i: int) -> tuple[torch.Tensor, torch.Tensor]:
        """Row i as (features, target)."""
        return self.X[i], self.y[i]


def make_model(n_features: int, hidden: int) -> nn.Module:
    """Linear, ReLU, Linear with one logit out (lessons B23-L4 and B23-L5).

    Raises:
        ValueError: If n_features or hidden is below 1.
    """
    if n_features < 1 or hidden < 1:
        raise ValueError(f"need sizes of at least 1, got {n_features} and {hidden}")
    return nn.Sequential(nn.Linear(n_features, hidden), nn.ReLU(), nn.Linear(hidden, 1))


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
    model.train()
    total, rows = 0.0, 0
    for x, y in loader:
        optimizer.zero_grad()
        loss = loss_fn(model(x).squeeze(1), y)
        loss.backward()
        optimizer.step()
        total += loss.item() * len(y)
        rows += len(y)
    if rows == 0:
        raise ValueError("the loader yielded no rows")
    return total / rows


def evaluate(
    model: nn.Module, loader: DataLoader[tuple[torch.Tensor, torch.Tensor]], loss_fn: nn.Module
) -> tuple[float, float]:
    """Mean loss and accuracy at a 0.5 threshold, in eval mode (lesson B16-L2).

    Returns:
        Mean loss per row, and the share of rows classified correctly.

    Raises:
        ValueError: If the loader yields no rows.
    """
    model.eval()
    total, correct, rows = 0.0, 0, 0
    with torch.no_grad():
        for x, y in loader:
            logits = model(x).squeeze(1)
            total += loss_fn(logits, y).item() * len(y)
            correct += int(((logits > 0).float() == y).sum().item())
            rows += len(y)
    if rows == 0:
        raise ValueError("the loader yielded no rows")
    return total / rows, correct / rows
