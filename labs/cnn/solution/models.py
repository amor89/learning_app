"""Reference solution for src/digits_cnn/models.py.

Read this only after your own version passes the tests.
"""

from __future__ import annotations

from torch import nn


def make_cnn(n_classes: int) -> nn.Module:
    """Two conv blocks and a linear classifier for 8 by 8 digits (lessons B24-L1 to B24-L3).

    Each block is a 3 by 3 convolution with padding 1, ReLU and MaxPool2d(2):
    8 by 8 becomes 4 by 4, then 2 by 2, with 16 and then 32 channels.

    Args:
        n_classes: Number of classes, one logit each.

    Returns:
        A model mapping (N, 1, 8, 8) to (N, n_classes) logits.

    Raises:
        ValueError: If n_classes is below 2.
    """
    if n_classes < 2:
        raise ValueError(f"need at least 2 classes, got {n_classes}")
    return nn.Sequential(
        nn.Conv2d(1, 16, kernel_size=3, padding=1),
        nn.ReLU(),
        nn.MaxPool2d(2),
        nn.Conv2d(16, 32, kernel_size=3, padding=1),
        nn.ReLU(),
        nn.MaxPool2d(2),
        nn.Flatten(),
        nn.Linear(32 * 2 * 2, n_classes),
    )
