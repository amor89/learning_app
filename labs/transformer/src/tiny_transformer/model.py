"""The classifier you write.

Each method raises NotImplementedError until you fill it in.
tests/test_model.py says what it must do.
"""

from __future__ import annotations

import torch
from torch import nn


class Classifier(nn.Module):
    """Token embeddings and positions, transformer blocks, mean over real tokens, linear head."""

    def __init__(
        self,
        vocab_size: int,
        d: int,
        heads: int,
        n_layers: int,
        max_len: int,
        use_positions: bool = True,
    ) -> None:
        """Build the layers. Positions are a fixed buffer, not weights (lesson B25-L5).

        Raises:
            ValueError: If n_layers is below 1.
        """
        raise NotImplementedError("Classifier.__init__")

    def forward(self, ids: torch.Tensor) -> torch.Tensor:
        """Two logits per sequence.

        Args:
            ids: Token IDs, shape (batch, length), padding 0 at the end.

        Returns:
            Shape (batch, 2).
        """
        raise NotImplementedError("Classifier.forward")
