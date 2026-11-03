"""Reference solution for src/finetune_lab/schedule.py.

Read this only after your own version passes the tests.
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
    if warmup_steps < 0 or warmup_steps >= total_steps:
        raise ValueError(f"need 0 <= warmup_steps < total_steps, got {warmup_steps}, {total_steps}")
    if step < 0:
        raise ValueError(f"step must not be negative, got {step}")
    if step < warmup_steps:
        return step / warmup_steps
    return max(0.0, (total_steps - step) / (total_steps - warmup_steps))
