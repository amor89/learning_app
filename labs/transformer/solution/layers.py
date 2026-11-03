"""Reference solutions for src/tiny_transformer/layers.py.

Read this only after your own version passes the tests. The repository's CI
copies this file over the stubs and runs the lab's tests.
"""

from __future__ import annotations

import math

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
    scores = q @ k.transpose(-2, -1) / math.sqrt(q.shape[-1])
    if allowed is not None:
        scores = scores.masked_fill(~allowed, float("-inf"))
    return torch.softmax(scores, dim=-1) @ v


def sinusoidal_positions(n: int, d: int) -> torch.Tensor:
    """Sinusoidal position encodings, shape (n, d) (lesson B25-L5).

    Raises:
        ValueError: If n is below 1 or d is not a positive even number.
    """
    if n < 1 or d < 2 or d % 2:
        raise ValueError(f"need n >= 1 and an even d >= 2, got {n} and {d}")
    pos = torch.arange(n, dtype=torch.float32)[:, None]
    angle = pos / 10000 ** (torch.arange(0, d, 2, dtype=torch.float32)[None, :] / d)
    pe = torch.zeros(n, d)
    pe[:, 0::2] = torch.sin(angle)
    pe[:, 1::2] = torch.cos(angle)
    return pe


class MultiHeadSelfAttention(nn.Module):
    """Multi-head self-attention built on attention() (lesson B25-L5)."""

    def __init__(self, d: int, heads: int) -> None:
        """Four d by d projections: queries, keys, values and output.

        Raises:
            ValueError: If d does not divide by heads.
        """
        super().__init__()
        if heads < 1 or d % heads:
            raise ValueError(f"d={d} must divide by heads={heads}")
        self.heads = heads
        self.q = nn.Linear(d, d)
        self.k = nn.Linear(d, d)
        self.v = nn.Linear(d, d)
        self.out = nn.Linear(d, d)

    def forward(self, x: torch.Tensor, is_pad: torch.Tensor) -> torch.Tensor:
        """Self-attention over (batch, length, d), ignoring padded keys.

        Args:
            x: Token vectors, shape (batch, length, d).
            is_pad: Boolean, shape (batch, length). True at padding.

        Returns:
            Shape (batch, length, d).
        """
        n, length, d = x.shape
        dh = d // self.heads

        def split(t: torch.Tensor) -> torch.Tensor:
            return t.reshape(n, length, self.heads, dh).transpose(1, 2)

        allowed = (~is_pad)[:, None, None, :]
        merged = attention(split(self.q(x)), split(self.k(x)), split(self.v(x)), allowed)
        return self.out(merged.transpose(1, 2).reshape(n, length, d))


class Block(nn.Module):
    """Pre-norm transformer block (lesson B25-L6)."""

    def __init__(self, d: int, heads: int) -> None:
        """Layer norms, self-attention and a feed-forward layer four times wider than d."""
        super().__init__()
        self.norm_1 = nn.LayerNorm(d)
        self.attn = MultiHeadSelfAttention(d, heads)
        self.norm_2 = nn.LayerNorm(d)
        self.ff = nn.Sequential(nn.Linear(d, 4 * d), nn.ReLU(), nn.Linear(4 * d, d))

    def forward(self, x: torch.Tensor, is_pad: torch.Tensor) -> torch.Tensor:
        """x + attention(norm(x)), then x + feed_forward(norm(x))."""
        x = x + self.attn(self.norm_1(x), is_pad)
        result: torch.Tensor = x + self.ff(self.norm_2(x))
        return result
