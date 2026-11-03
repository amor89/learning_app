"""The synthetic task. Needs NumPy only."""

from __future__ import annotations

import numpy as np
from tiny_transformer.data import MAX_LEN, MIN_LEN, N_TOKENS, make_sequences


def test_shapes_padding_and_labels() -> None:
    ids, labels = make_sequences(500, 3)
    assert ids.shape == (500, MAX_LEN) and labels.shape == (500,)
    lengths = (ids != 0).sum(axis=1)
    assert lengths.min() >= MIN_LEN and lengths.max() <= MAX_LEN
    for row, length in zip(ids, lengths, strict=True):
        assert (row[:length] != 0).all() and (row[length:] == 0).all()
    last = ids[np.arange(500), lengths - 1]
    assert np.array_equal(labels, (ids[:, 0] == last).astype(int))
    assert ids.max() <= N_TOKENS and 0.4 < labels.mean() < 0.6


def test_seeded() -> None:
    a, b = make_sequences(50, 7), make_sequences(50, 7)
    assert np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])
