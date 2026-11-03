"""Reference solution for src/finetune_lab/lora.py.

Read this only after your own version passes the tests.
"""

from __future__ import annotations

import math

import torch
from torch import nn


class LoRALinear(nn.Module):
    """A frozen linear layer plus a trainable low-rank update (lesson B26-L3).

    The output is base(x) + (alpha / r) * x @ A.T @ B.T. B starts at zero, so
    the layer starts out equal to the base layer.
    """

    base: nn.Linear
    scaling: float

    def __init__(self, base: nn.Linear, r: int, alpha: float) -> None:
        """Freeze base and create A, shape (r, in_features), and B, shape (out_features, r).

        Initialise A at random, as peft does with nn.init.kaiming_uniform_(A, a=math.sqrt(5)),
        and B at zero.

        Raises:
            ValueError: If r is below 1.
        """
        super().__init__()
        if r < 1:
            raise ValueError(f"r must be at least 1, got {r}")
        self.base = base
        base.requires_grad_(False)
        self.A = nn.Parameter(torch.empty(r, base.in_features))
        nn.init.kaiming_uniform_(self.A, a=math.sqrt(5))
        self.B = nn.Parameter(torch.zeros(base.out_features, r))
        self.scaling = alpha / r

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Base output plus the scaled low-rank update."""
        update = (x @ self.A.T @ self.B.T) * self.scaling
        result: torch.Tensor = self.base(x) + update
        return result

    def merged(self) -> nn.Linear:
        """A plain linear layer with the update folded into its weight.

        Returns:
            nn.Linear whose weight is base.weight + scaling * B @ A, same bias.
        """
        out = nn.Linear(
            self.base.in_features, self.base.out_features, bias=self.base.bias is not None
        )
        with torch.no_grad():
            out.weight.copy_(self.base.weight + self.scaling * self.B @ self.A)
            if self.base.bias is not None:
                out.bias.copy_(self.base.bias)
        return out


def add_lora(model: nn.Module, r: int, alpha: float) -> int:
    """Wrap the query and value projections of every attention layer in LoRALinear.

    Args:
        model: A model with model.encoder.blocks, each with attn.q and attn.v.
        r: Rank of the update.
        alpha: Scale numerator; the update is multiplied by alpha / r.

    Returns:
        The number of layers wrapped.
    """
    wrapped = 0
    for block in model.encoder.blocks:
        block.attn.q = LoRALinear(block.attn.q, r, alpha)
        block.attn.v = LoRALinear(block.attn.v, r, alpha)
        wrapped += 2
    return wrapped
