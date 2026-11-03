"""Reference solution for src/tiny_transformer/model.py.

Read this only after your own version passes the tests.
"""

from __future__ import annotations

import torch
from tiny_transformer.layers import Block, sinusoidal_positions
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
        super().__init__()
        if n_layers < 1:
            raise ValueError(f"need at least one layer, got {n_layers}")
        self.tokens = nn.Embedding(vocab_size, d, padding_idx=0)
        self.use_positions = use_positions
        self.register_buffer("positions", sinusoidal_positions(max_len, d))
        self.blocks = nn.ModuleList(Block(d, heads) for _ in range(n_layers))
        self.norm = nn.LayerNorm(d)
        self.head = nn.Linear(d, 2)

    def forward(self, ids: torch.Tensor) -> torch.Tensor:
        """Two logits per sequence.

        Args:
            ids: Token IDs, shape (batch, length), padding 0 at the end.

        Returns:
            Shape (batch, 2).
        """
        is_pad = ids == 0
        x = self.tokens(ids)
        if self.use_positions:
            x = x + self.positions[: ids.shape[1]]
        for block in self.blocks:
            x = block(x, is_pad)
        x = self.norm(x)
        keep = (~is_pad).unsqueeze(-1).float()
        pooled = (x * keep).sum(dim=1) / keep.sum(dim=1).clamp(min=1.0)
        logits: torch.Tensor = self.head(pooled)
        return logits
