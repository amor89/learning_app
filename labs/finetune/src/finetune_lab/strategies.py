"""The fine-tuning set-up you write: load pretrained weights and choose what trains.

Each function raises NotImplementedError until you fill it in.
tests/test_strategies.py says what each must do.
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
    raise NotImplementedError("load_backbone")


def set_trainable(model: nn.Module, prefixes: tuple[str, ...]) -> int:
    """Train only parameters whose name starts with one of the prefixes (lesson B26-L1).

    Args:
        model: Any module.
        prefixes: Name prefixes to train, for example ("head.",). ("",) trains everything.

    Returns:
        The number of trainable values.
    """
    raise NotImplementedError("set_trainable")


def count_parameters(model: nn.Module) -> tuple[int, int]:
    """Trainable and total parameter values.

    Args:
        model: Any module.

    Returns:
        (trainable, total).
    """
    raise NotImplementedError("count_parameters")
