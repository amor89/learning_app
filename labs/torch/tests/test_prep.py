"""What prep.py must do. These tests need NumPy only, not PyTorch."""

from __future__ import annotations

import math

import numpy as np
import pytest
from survey_torch.prep import EarlyStopping, Standardiser, split_indices

# split_indices (lesson B23-L6) ----------------------------------------------


def test_split_covers_every_row_once() -> None:
    train, val = split_indices(100, 0.2, np.random.default_rng(0))
    assert len(train) == 80 and len(val) == 20
    assert sorted(np.concatenate([train, val]).tolist()) == list(range(100))


def test_split_is_seeded() -> None:
    train, val = split_indices(50, 0.2, np.random.default_rng(3))
    order = np.random.default_rng(3).permutation(50)
    assert np.array_equal(val, order[:10]) and np.array_equal(train, order[10:])


@pytest.mark.parametrize(("n", "share"), [(10, 0.0), (10, 1.0), (10, 1.5), (1, 0.5), (3, 0.01)])
def test_split_rejects_empty_parts(n: int, share: float) -> None:
    with pytest.raises(ValueError):
        split_indices(n, share, np.random.default_rng(0))


# Standardiser (lessons B23-L6 and B10-L2) -----------------------------------


def test_standardiser_uses_training_statistics() -> None:
    scaler = Standardiser().fit(np.array([[1.0, 10.0], [3.0, 30.0]]))
    assert np.allclose(scaler.transform(np.array([[5.0, 50.0]])), [[3.0, 3.0]])


def test_standardiser_constant_column() -> None:
    scaler = Standardiser().fit(np.array([[1.0, 5.0], [3.0, 5.0]]))
    assert np.allclose(scaler.transform(np.array([[2.0, 7.0]])), [[0.0, 2.0]])


def test_standardiser_guards() -> None:
    with pytest.raises(ValueError):
        Standardiser().fit(np.empty((0, 2)))
    with pytest.raises(ValueError):
        Standardiser().fit(np.array([[1.0, np.nan]]))
    with pytest.raises(RuntimeError):
        Standardiser().transform(np.ones((1, 2)))


# EarlyStopping (lesson B16-L2) ----------------------------------------------


def test_early_stopping_counts_epochs_without_improvement() -> None:
    stopper = EarlyStopping(patience=2)
    assert stopper.step(0.5, {"w": [1]}) is False
    assert stopper.step(0.6, {"w": [2]}) is False
    assert stopper.step(0.7, {"w": [3]}) is True
    assert stopper.best_loss == 0.5 and stopper.best_state == {"w": [1]}


def test_early_stopping_keeps_a_deep_copy() -> None:
    stopper = EarlyStopping(patience=3)
    state = {"w": [1.0, 2.0]}
    stopper.step(0.5, state)
    state["w"][0] = 99.0
    assert stopper.best_state == {"w": [1.0, 2.0]}


def test_early_stopping_min_delta_and_reset() -> None:
    stopper = EarlyStopping(patience=2, min_delta=0.01)
    stopper.step(0.50, {"e": 1})
    assert stopper.step(0.495, {"e": 2}) is False
    assert stopper.bad_epochs == 1 and stopper.best_state == {"e": 1}
    assert stopper.step(0.40, {"e": 3}) is False
    assert stopper.bad_epochs == 0 and stopper.best_state == {"e": 3}


def test_early_stopping_starts_empty_and_checks_arguments() -> None:
    stopper = EarlyStopping(patience=1)
    assert stopper.best_loss == math.inf and stopper.best_state is None
    with pytest.raises(ValueError):
        EarlyStopping(patience=0)
    with pytest.raises(ValueError):
        EarlyStopping(patience=2, min_delta=-0.1)
