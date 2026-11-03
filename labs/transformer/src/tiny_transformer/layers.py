"""The layers you write: attention, positions, multi-head self-attention, the block.

Each function and method raises NotImplementedError until you fill it in.
tests/test_layers.py says what each must do, and checks attention against
torch.nn.functional.scaled_dot_product_attention.
"""

from __future__ import annotations

import torch
from torch import nn


def attention(
    q: torch.Tensor, k: torch.Tensor, v: torch.Tensor, allowed: torch.Tensor | None = None
) -> torch.Tensor:
    """Scaled dot-product attention (lessons B25-L3 and B25-L4).

    Args:
        q: Queries, shape (..., Lq, d).
        k: Keys, shape (..., Lk, d).
        v: Values, shape (..., Lk, dv).
        allowed: Boolean, broadcastable to (..., Lq, Lk). True where attention may look.

    Returns:
        Outputs, shape (..., Lq, dv).
    """
    raise NotImplementedError("attention")


def sinusoidal_positions(n: int, d: int) -> torch.Tensor:
    """Sinusoidal position encodings, shape (n, d) (lesson B25-L5).

    Raises:
        ValueError: If n is below 1 or d is not a positive even number.
    """
    raise NotImplementedError("sinusoidal_positions")


class MultiHeadSelfAttention(nn.Module):
    """Multi-head self-attention built on attention() (lesson B25-L5)."""

    def __init__(self, d: int, heads: int) -> None:
        """Four d by d projections: queries, keys, values and output.

        Raises:
            ValueError: If d does not divide by heads.
        """
        raise NotImplementedError("MultiHeadSelfAttention.__init__")

    def forward(self, x: torch.Tensor, is_pad: torch.Tensor) -> torch.Tensor:
        """Self-attention over (batch, length, d), ignoring padded keys.

        Args:
            x: Token vectors, shape (batch, length, d).
            is_pad: Boolean, shape (batch, length). True at padding.

        Returns:
            Shape (batch, length, d).
        """
        raise NotImplementedError("MultiHeadSelfAttention.forward")


class Block(nn.Module):
    """Pre-norm transformer block (lesson B25-L6)."""

    def __init__(self, d: int, heads: int) -> None:
        """Layer norms, self-attention and a feed-forward layer four times wider than d."""
        raise NotImplementedError("Block.__init__")

    def forward(self, x: torch.Tensor, is_pad: torch.Tensor) -> torch.Tensor:
        """x + attention(norm(x)), then x + feed_forward(norm(x))."""
        raise NotImplementedError("Block.forward")
