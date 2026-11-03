"""What nn_steps.py and the full run must do. Skipped when PyTorch is missing."""

from __future__ import annotations

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from survey_torch.nn_steps import SurveyRows, evaluate, make_model, train_one_epoch  # noqa: E402
from survey_torch.train import TrainConfig, fit  # noqa: E402
from torch import nn  # noqa: E402
from torch.utils.data import DataLoader  # noqa: E402

# SurveyRows and make_model (lessons B23-L1, B23-L4, B23-L6) ------------------


def test_rows_are_float32_tensors() -> None:
    rows = SurveyRows(np.ones((5, 3)), np.array([0, 1, 0, 1, 1]))
    x, y = rows[1]
    assert len(rows) == 5
    assert x.dtype == torch.float32 and y.dtype == torch.float32
    assert x.shape == (3,) and y.item() == 1.0
    with pytest.raises(ValueError):
        SurveyRows(np.ones((5, 3)), np.ones(4))


def test_model_shape_and_parameters() -> None:
    model = make_model(9, 32)
    assert model(torch.zeros(4, 9)).shape == (4, 1)
    assert sum(p.numel() for p in model.parameters()) == 9 * 32 + 32 + 32 + 1
    assert not any(isinstance(m, nn.Sigmoid) for m in model.modules())
    with pytest.raises(ValueError):
        make_model(0, 32)


# train_one_epoch and evaluate (lessons B23-L3, B23-L5, B16-L2) ---------------


def _easy_loader(shuffle: bool) -> DataLoader:
    rng = np.random.default_rng(0)
    X = rng.normal(size=(200, 2))
    y = (X[:, 0] > 0).astype(float)
    return DataLoader(SurveyRows(X, y), batch_size=32, shuffle=shuffle)


def test_training_lowers_the_loss() -> None:
    torch.manual_seed(0)
    model = make_model(2, 8)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-2)
    loss_fn = nn.BCEWithLogitsLoss()
    losses = [train_one_epoch(model, _easy_loader(True), loss_fn, optimizer) for _ in range(20)]
    assert all(isinstance(v, float) for v in losses)
    assert losses[-1] < 0.5 * losses[0], losses
    assert model.training


def test_evaluate_scores_without_changing_the_model() -> None:
    model = nn.Sequential(nn.Linear(2, 1))
    with torch.no_grad():
        model[0].weight.copy_(torch.tensor([[10.0, 0.0]]))
        model[0].bias.zero_()
    before = [p.clone() for p in model.parameters()]
    loss, accuracy = evaluate(model, _easy_loader(False), nn.BCEWithLogitsLoss())
    assert accuracy == 1.0 and 0 < loss < 0.2
    assert not model.training
    assert all(torch.equal(a, b) for a, b in zip(before, model.parameters(), strict=True))
    assert all(p.grad is None for p in model.parameters())


# The full run (train.py) -------------------------------------------------------


@pytest.fixture(scope="module")
def run() -> object:
    return fit(TrainConfig())


def test_network_beats_the_baseline(run: object) -> None:
    assert run.model_loss < run.baseline_loss, run
    assert run.model_accuracy >= run.baseline_accuracy - 0.01, run


def test_best_weights_are_restored(run: object) -> None:
    best_val = min(val for _, val in run.history)
    assert abs(run.model_loss - best_val) < 1e-6, (run.model_loss, best_val)
    assert run.epochs_run < TrainConfig().max_epochs


def test_same_seed_same_result(run: object) -> None:
    again = fit(TrainConfig())
    assert again.model_loss == run.model_loss and again.history == run.history
