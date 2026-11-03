"""LoRA you write: a frozen linear layer plus a trainable low-rank update.

Each method raises NotImplementedError until you fill it in.
tests/test_strategies.py says what each must do.
"""

from __future__ import annotations

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
        raise NotImplementedError("LoRALinear.__init__")

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Base output plus the scaled low-rank update."""
        raise NotImplementedError("LoRALinear.forward")

    def merged(self) -> nn.Linear:
        """A plain linear layer with the update folded into its weight.

        Returns:
            nn.Linear whose weight is base.weight + scaling * B @ A, same bias.
        """
        raise NotImplementedError("LoRALinear.merged")


def add_lora(model: nn.Module, r: int, alpha: float) -> int:
    """Wrap the query and value projections of every attention layer in LoRALinear.

    Args:
        model: A model with model.encoder.blocks, each with attn.q and attn.v.
        r: Rank of the update.
        alpha: Scale numerator; the update is multiplied by alpha / r.

    Returns:
        The number of layers wrapped.
    """
    raise NotImplementedError("add_lora")
