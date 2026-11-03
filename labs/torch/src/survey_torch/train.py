"""Fit the network and a logistic regression baseline on the same split."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss
from torch import nn
from torch.utils.data import DataLoader

from survey_torch.data import make_survey_data
from survey_torch.nn_steps import SurveyRows, evaluate, make_model, train_one_epoch
from survey_torch.prep import EarlyStopping, Standardiser, split_indices


@dataclass(frozen=True)
class TrainConfig:
    """Every setting of one run. Log it with the results."""

    n_rows: int = 6000
    data_seed: int = 7
    seed: int = 0
    val_share: float = 0.2
    hidden: int = 32
    lr: float = 3e-3
    batch_size: int = 64
    max_epochs: int = 100
    patience: int = 10
    min_delta: float = 1e-4

    def __post_init__(self) -> None:
        """Fail fast on settings that cannot train."""
        if self.lr <= 0 or self.batch_size < 1 or self.max_epochs < 1 or self.hidden < 1:
            raise ValueError(f"invalid config: {self}")


@dataclass(frozen=True)
class RunResult:
    """Validation scores of the baseline and the network, and the loss curve."""

    baseline_loss: float
    baseline_accuracy: float
    model_loss: float
    model_accuracy: float
    epochs_run: int
    history: list[tuple[float, float]] = field(default_factory=list)


def baseline_scores(
    X_train: np.ndarray, y_train: np.ndarray, X_val: np.ndarray, y_val: np.ndarray
) -> tuple[float, float]:
    """Log loss and accuracy of logistic regression on the validation rows."""
    model = LogisticRegression(max_iter=1000).fit(X_train, y_train)
    proba = model.predict_proba(X_val)[:, 1]
    return float(log_loss(y_val, proba)), float(accuracy_score(y_val, proba > 0.5))


def fit(config: TrainConfig) -> RunResult:
    """Train with early stopping, restore the best weights, and score both models.

    Args:
        config: The run settings.

    Returns:
        Validation loss and accuracy for the baseline and the network, the
        number of epochs run, and (train loss, validation loss) per epoch.

    Raises:
        RuntimeError: If early stopping recorded no best state.
    """
    torch.manual_seed(config.seed)
    rng = np.random.default_rng(config.seed)
    X, y = make_survey_data(config.n_rows, config.data_seed)
    train_idx, val_idx = split_indices(len(y), config.val_share, rng)
    scaler = Standardiser().fit(X[train_idx])
    X_train, X_val = scaler.transform(X[train_idx]), scaler.transform(X[val_idx])
    y_train, y_val = y[train_idx], y[val_idx]

    loader_gen = torch.Generator().manual_seed(config.seed)
    train_loader = DataLoader(
        SurveyRows(X_train, y_train),
        batch_size=config.batch_size,
        shuffle=True,
        generator=loader_gen,
    )
    val_loader = DataLoader(SurveyRows(X_val, y_val), batch_size=1024)

    model = make_model(X.shape[1], config.hidden)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.lr)
    loss_fn = nn.BCEWithLogitsLoss()
    stopper = EarlyStopping(config.patience, config.min_delta)
    history: list[tuple[float, float]] = []
    for _ in range(config.max_epochs):
        train_loss = train_one_epoch(model, train_loader, loss_fn, optimizer)
        val_loss, _ = evaluate(model, val_loader, loss_fn)
        history.append((train_loss, val_loss))
        if stopper.step(val_loss, model.state_dict()):
            break
    if stopper.best_state is None:
        raise RuntimeError("early stopping recorded no best state")
    model.load_state_dict(stopper.best_state)
    model_loss, model_accuracy = evaluate(model, val_loader, loss_fn)
    base_loss, base_accuracy = baseline_scores(X_train, y_train, X_val, y_val)
    return RunResult(base_loss, base_accuracy, model_loss, model_accuracy, len(history), history)
