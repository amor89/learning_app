"""What model.py and the full run must do. Skipped when PyTorch is missing."""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from tiny_transformer.model import Classifier  # noqa: E402
from tiny_transformer.train import TrainConfig, run  # noqa: E402


def test_classifier_shape_and_padding_invariance() -> None:
    torch.manual_seed(0)
    model = Classifier(9, 16, 4, 2, 12).eval()
    ids = torch.tensor([[3, 4, 5, 3, 0, 0], [1, 2, 3, 4, 5, 6]])
    longer = torch.cat([ids, torch.zeros(2, 4, dtype=torch.long)], dim=1)
    assert model(ids).shape == (2, 2)
    assert torch.allclose(model(ids), model(longer), atol=1e-5)


def test_positions_change_the_prediction() -> None:
    torch.manual_seed(0)
    with_pos = Classifier(9, 16, 4, 1, 12).eval()
    without = Classifier(9, 16, 4, 1, 12, use_positions=False).eval()
    without.load_state_dict(with_pos.state_dict())
    ids, shuffled = torch.tensor([[3, 4, 5, 6]]), torch.tensor([[6, 5, 4, 3]])
    assert not torch.allclose(with_pos(ids), with_pos(shuffled), atol=1e-6)
    assert torch.allclose(without(ids), without(shuffled), atol=1e-5)


def test_learns_the_task_only_with_positions() -> None:
    assert run(TrainConfig()).val_accuracy >= 0.95
    assert run(TrainConfig(use_positions=False, epochs=10)).val_accuracy <= 0.65
