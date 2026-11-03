"""What vision.py must do. These tests need NumPy only, not PyTorch."""

from __future__ import annotations

import warnings

import numpy as np
import pytest
from digits_cnn.vision import add_channel, confusion, random_shift, recall_by_class

# add_channel (lessons B24-L2 and B24-L4) --------------------------------------


def test_add_channel_shape_and_dtype() -> None:
    out = add_channel(np.ones((5, 8, 8)))
    assert out.shape == (5, 1, 8, 8) and out.dtype == np.float32


def test_add_channel_keeps_values() -> None:
    images = np.arange(32.0).reshape(2, 4, 4) / 32
    assert np.array_equal(add_channel(images)[:, 0], images.astype(np.float32))


@pytest.mark.parametrize("shape", [(8, 8), (2, 1, 8, 8), (0, 8, 8)])
def test_add_channel_rejects_bad_shapes(shape: tuple[int, ...]) -> None:
    with pytest.raises(ValueError):
        add_channel(np.ones(shape))


# random_shift (lesson B24-L4) -------------------------------------------------


def test_shift_matches_a_seeded_window() -> None:
    x = np.arange(16.0).reshape(4, 4)
    out = random_shift(x, 1, np.random.default_rng(0))
    top, left = np.random.default_rng(0).integers(0, 3, size=2)
    assert np.array_equal(out, np.pad(x, 1)[top : top + 4, left : left + 4])


def test_shift_zero_is_identity_and_shape_is_kept() -> None:
    x = np.arange(6.0).reshape(2, 3)
    assert np.array_equal(random_shift(x, 0, np.random.default_rng(1)), x)
    assert random_shift(np.ones((8, 8)), 2, np.random.default_rng(2)).shape == (8, 8)


def test_shift_guards() -> None:
    with pytest.raises(ValueError):
        random_shift(np.ones(4), 1, np.random.default_rng(0))
    with pytest.raises(ValueError):
        random_shift(np.ones((2, 2)), -1, np.random.default_rng(0))


# confusion and recall_by_class (lesson B24-L6) ---------------------------------


def test_confusion_counts() -> None:
    cm = confusion(np.array([0, 0, 1, 1, 2, 2]), np.array([0, 1, 1, 1, 2, 0]), 3)
    assert cm.tolist() == [[1, 1, 0], [0, 2, 0], [1, 0, 1]]
    assert np.issubdtype(cm.dtype, np.integer)


def test_confusion_size_and_guards() -> None:
    assert confusion(np.array([0]), np.array([1]), 4).shape == (4, 4)
    with pytest.raises(ValueError):
        confusion(np.array([0, 1]), np.array([0]), 2)
    with pytest.raises(ValueError):
        confusion(np.array([0, 3]), np.array([0, 1]), 3)


def test_recall_by_class() -> None:
    out = recall_by_class(np.array([[1, 1, 0], [0, 2, 0], [1, 0, 1]]))
    assert np.allclose(out, [0.5, 1.0, 0.5])
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        empty = recall_by_class(np.array([[2, 0], [0, 0]]))
    assert empty[0] == 1.0 and np.isnan(empty[1])
    with pytest.raises(ValueError):
        recall_by_class(np.ones((2, 3)))
