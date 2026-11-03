"""What models.py and the full run must do. Skipped when PyTorch is missing."""

from __future__ import annotations

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from digits_cnn.models import make_cnn  # noqa: E402
from digits_cnn.train import ModelResult, TrainConfig, run  # noqa: E402


def test_cnn_shape_and_parameters() -> None:
    model = make_cnn(10)
    assert model(torch.zeros(5, 1, 8, 8)).shape == (5, 10)
    assert sum(p.numel() for p in model.parameters()) == 6090
    assert any(isinstance(m, torch.nn.Conv2d) for m in model.modules())
    with pytest.raises(ValueError):
        make_cnn(1)


@pytest.fixture(scope="module")
def results() -> dict[str, ModelResult]:
    return {r.name: r for r in run(TrainConfig())}


def test_cnn_beats_the_dense_network(results: dict[str, ModelResult]) -> None:
    cnn, dense = results["cnn"], results["dense"]
    assert cnn.val_loss < dense.val_loss, (cnn.val_loss, dense.val_loss)
    assert cnn.val_accuracy >= 0.98, cnn.val_accuracy
    assert cnn.confusion.sum() == 360  # train_test_split rounds the 20% share up


def test_recall_is_reported_for_every_digit(results: dict[str, ModelResult]) -> None:
    recall = results["cnn"].recall
    assert recall.shape == (10,) and not np.isnan(recall).any()
    assert recall.min() >= 0.9, recall


def test_same_seed_same_result(results: dict[str, ModelResult]) -> None:
    again = {r.name: r for r in run(TrainConfig())}
    assert again["cnn"].val_loss == results["cnn"].val_loss
    assert np.array_equal(again["cnn"].confusion, results["cnn"].confusion)
