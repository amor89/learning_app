"""Reference solution for src/finetune_lab/strategies.py.

Read this only after your own version passes the tests.
"""

from __future__ import annotations

import torch
from torch import nn

BACKBONE_PREFIX = "encoder."


def load_backbone(model: nn.Module, checkpoint: dict[str, torch.Tensor]) -> list[str]:
    """Copy the encoder weights from a pretraining checkpoint into a new model (lesson B26-L1).

    Args:
        model: A model whose encoder sits under `encoder.`, with a new head.
        checkpoint: A state_dict saved after pretraining. Its own head is left out.

    Returns:
        The model's keys that the checkpoint did not fill, sorted.

    Raises:
        ValueError: If the checkpoint has no encoder keys, or any encoder key
            of the model stays missing, or an encoder key is unexpected.
    """
    backbone = {k: v for k, v in checkpoint.items() if k.startswith(BACKBONE_PREFIX)}
    if not backbone:
        raise ValueError("checkpoint has no keys starting with 'encoder.'")
    result = model.load_state_dict(backbone, strict=False)
    missing_backbone = [k for k in result.missing_keys if k.startswith(BACKBONE_PREFIX)]
    if missing_backbone or result.unexpected_keys:
        raise ValueError(
            f"encoder did not load: missing {missing_backbone}, unexpected {result.unexpected_keys}"
        )
    return sorted(result.missing_keys)


def set_trainable(model: nn.Module, prefixes: tuple[str, ...]) -> int:
    """Train only parameters whose name starts with one of the prefixes (lesson B26-L1).

    Args:
        model: Any module.
        prefixes: Name prefixes to train, for example ("head.",). ("",) trains everything.

    Returns:
        The number of trainable values.
    """
    trainable = 0
    for name, param in model.named_parameters():
        param.requires_grad_(name.startswith(prefixes))
        if param.requires_grad:
            trainable += param.numel()
    return trainable


def count_parameters(model: nn.Module) -> tuple[int, int]:
    """Trainable and total parameter values.

    Args:
        model: Any module.

    Returns:
        (trainable, total).
    """
    params = list(model.parameters())
    return sum(p.numel() for p in params if p.requires_grad), sum(p.numel() for p in params)
