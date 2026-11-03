"""An encoder with two heads: one fills in masked tokens, one classifies sequences."""

from __future__ import annotations

import torch
from torch import nn

from finetune_lab.layers import Block, sinusoidal_positions


class Encoder(nn.Module):
    """Token embeddings plus sinusoidal positions, pre-norm blocks and a final LayerNorm."""

    def __init__(self, vocab_size: int, d: int, heads: int, n_layers: int, max_len: int) -> None:
        """Build the layers. No padding: every sequence has the same length.

        Raises:
            ValueError: If n_layers is below 1.
        """
        super().__init__()
        if n_layers < 1:
            raise ValueError(f"need at least one layer, got {n_layers}")
        self.tokens = nn.Embedding(vocab_size, d)
        self.register_buffer("positions", sinusoidal_positions(max_len, d))
        self.blocks = nn.ModuleList(Block(d, heads) for _ in range(n_layers))
        self.norm = nn.LayerNorm(d)

    def forward(self, ids: torch.Tensor) -> torch.Tensor:
        """One vector per token, shape (batch, length, d)."""
        positions: torch.Tensor = self.positions
        x = self.tokens(ids) + positions[: ids.shape[1]]
        no_pad = torch.zeros_like(ids, dtype=torch.bool)
        for block in self.blocks:
            x = block(x, no_pad)
        result: torch.Tensor = self.norm(x)
        return result


class MaskedLM(nn.Module):
    """Encoder plus a head that scores every vocabulary token at every position."""

    def __init__(self, encoder: Encoder, d: int, vocab_size: int) -> None:
        """Attach a linear head from d to vocab_size."""
        super().__init__()
        self.encoder = encoder
        self.head = nn.Linear(d, vocab_size)

    def forward(self, ids: torch.Tensor) -> torch.Tensor:
        """Logits of shape (batch, length, vocab_size)."""
        logits: torch.Tensor = self.head(self.encoder(ids))
        return logits


class Classifier(nn.Module):
    """Encoder, mean over positions, and a linear head with one logit per class."""

    def __init__(self, encoder: Encoder, d: int, n_classes: int) -> None:
        """Attach a linear head from d to n_classes."""
        super().__init__()
        self.encoder = encoder
        self.head = nn.Linear(d, n_classes)

    def forward(self, ids: torch.Tensor) -> torch.Tensor:
        """Logits of shape (batch, n_classes)."""
        logits: torch.Tensor = self.head(self.encoder(ids).mean(dim=1))
        return logits
