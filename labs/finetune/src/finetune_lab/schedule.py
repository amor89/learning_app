"""The learning-rate schedule you write.

The function raises NotImplementedError until you fill it in.
tests/test_data_and_schedule.py says what it must do, and runs without PyTorch.
"""

from __future__ import annotations


def warmup_linear(step: int, warmup_steps: int, total_steps: int) -> float:
    """Learning-rate factor: linear warm-up from 0 to 1, then linear decay to 0 (lesson B26-L2).

    Args:
        step: Optimiser steps taken so far, from 0.
        warmup_steps: Steps to rise from 0 to 1. Zero means start at 1.
        total_steps: Step at which the factor reaches 0.

    Returns:
        The factor in [0, 1].

    Raises:
        ValueError: If warmup_steps is negative or not below total_steps, or step is negative.
    """
    raise NotImplementedError("warmup_linear")
