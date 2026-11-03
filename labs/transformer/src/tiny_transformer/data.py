"""Synthetic sequences: does a sequence start and end with the same token?

Tokens are 1 to N_TOKENS, padding is 0 at the end. Half the sequences end with
their first token. Answering needs position: the same tokens in another order
change the label, so a model that cannot see order is stuck near chance.
"""

from __future__ import annotations

import numpy as np

PAD = 0
N_TOKENS = 8
MAX_LEN = 12
MIN_LEN = 4


def make_sequences(n: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Right-padded token IDs and labels (1 when the first and last real tokens match).

    Args:
        n: Number of sequences.
        seed: Seed for the generator.

    Returns:
        ids of shape (n, MAX_LEN), int64, and labels of shape (n,), int64.

    Raises:
        ValueError: If n is below 1.
    """
    if n < 1:
        raise ValueError(f"n must be at least 1, got {n}")
    rng = np.random.default_rng(seed)
    ids = np.zeros((n, MAX_LEN), dtype=np.int64)
    labels = np.zeros(n, dtype=np.int64)
    for row in range(n):
        length = int(rng.integers(MIN_LEN, MAX_LEN + 1))
        tokens = rng.integers(1, N_TOKENS + 1, size=length)
        match = bool(rng.random() < 0.5)
        if match:
            tokens[-1] = tokens[0]
        else:
            others = [t for t in range(1, N_TOKENS + 1) if t != tokens[0]]
            tokens[-1] = others[int(rng.integers(len(others)))]
        ids[row, :length] = tokens
        labels[row] = int(match)
    return ids, labels
