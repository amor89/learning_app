"""Synthetic sequences that follow a hidden step, with a little noise.

Each sequence counts round a ring of N_TOKENS tokens from a random start, in
steps of 1, 2 or 3. The label is the step: 0, 1 or 2. Pretraining sees many
unlabelled sequences and fills in masked tokens. Fine-tuning sees a few labelled
ones.
"""

from __future__ import annotations

import numpy as np

N_TOKENS = 10
LENGTH = 12
MASK = N_TOKENS + 1
VOCAB_SIZE = N_TOKENS + 2
STEPS = (1, 2, 3)


def make_sequences(n: int, seed: int, noise: float = 0.1) -> tuple[np.ndarray, np.ndarray]:
    """Sequences of token IDs 1 to N_TOKENS and the index of each one's step.

    Args:
        n: Number of sequences.
        seed: Seed for the generator.
        noise: Share of tokens replaced by a random token.

    Returns:
        ids of shape (n, LENGTH), int64, and labels of shape (n,), int64 in 0 to 2.

    Raises:
        ValueError: If n is below 1 or noise is outside 0 to 1.
    """
    if n < 1:
        raise ValueError(f"n must be at least 1, got {n}")
    if not 0.0 <= noise <= 1.0:
        raise ValueError(f"noise must be in [0, 1], got {noise}")
    rng = np.random.default_rng(seed)
    start = rng.integers(0, N_TOKENS, n)
    labels = rng.integers(0, len(STEPS), n)
    step = np.asarray(STEPS)[labels]
    ids = (start[:, None] + np.arange(LENGTH)[None, :] * step[:, None]) % N_TOKENS + 1
    replace = rng.random((n, LENGTH)) < noise
    ids = np.where(replace, rng.integers(1, N_TOKENS + 1, (n, LENGTH)), ids)
    return ids.astype(np.int64), labels.astype(np.int64)
