"""What the data and schedule.py must do. Runs without PyTorch."""

from __future__ import annotations

import numpy as np
import pytest
from finetune_lab.data import LENGTH, N_TOKENS, STEPS, make_sequences
from finetune_lab.schedule import warmup_linear


def test_sequences_follow_their_step() -> None:
    ids, labels = make_sequences(200, seed=0, noise=0.0)
    assert ids.shape == (200, LENGTH) and labels.shape == (200,)
    assert ids.min() >= 1 and ids.max() <= N_TOKENS
    step = np.asarray(STEPS)[labels]
    assert np.all((ids[:, 1:] - ids[:, :-1]) % N_TOKENS == step[:, None] % N_TOKENS)


def test_sequences_are_seeded_and_noisy() -> None:
    a, _ = make_sequences(50, seed=3)
    b, _ = make_sequences(50, seed=3)
    clean, _ = make_sequences(50, seed=3, noise=0.0)
    assert np.array_equal(a, b)
    assert 0.02 < float(np.mean(a != clean)) < 0.2


def test_warmup_rises_linearly() -> None:
    assert [warmup_linear(s, 4, 10) for s in range(5)] == [0.0, 0.25, 0.5, 0.75, 1.0]


def test_decay_reaches_zero_and_stays() -> None:
    assert warmup_linear(7, 4, 10) == pytest.approx(0.5)
    assert warmup_linear(10, 4, 10) == 0.0
    assert warmup_linear(12, 4, 10) == 0.0


def test_no_warmup_starts_at_one() -> None:
    assert warmup_linear(0, 0, 10) == 1.0
    assert warmup_linear(5, 0, 10) == pytest.approx(0.5)


@pytest.mark.parametrize(("step", "warmup", "total"), [(0, 10, 10), (0, -1, 10), (-1, 2, 10)])
def test_schedule_guards(step: int, warmup: int, total: int) -> None:
    with pytest.raises(ValueError):
        warmup_linear(step, warmup, total)
