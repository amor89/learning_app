"""Train a dense network and the CNN on the same split, and compare them."""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass

import numpy as np
import torch
from sklearn.model_selection import train_test_split
from torch import nn
from torch.utils.data import DataLoader, Dataset

from digits_cnn.data import N_CLASSES, load_digit_images
from digits_cnn.models import make_cnn
from digits_cnn.vision import add_channel, confusion, random_shift, recall_by_class


@dataclass(frozen=True)
class TrainConfig:
    """Every setting of one run. Log it with the results."""

    seed: int = 0
    val_share: float = 0.2
    augment: bool = False
    max_shift: int = 1
    lr: float = 3e-3
    batch_size: int = 64
    max_epochs: int = 60
    patience: int = 8

    def __post_init__(self) -> None:
        """Fail fast on settings that cannot train."""
        if not 0 < self.val_share < 1 or self.lr <= 0 or self.batch_size < 1:
            raise ValueError(f"invalid config: {self}")


@dataclass(frozen=True)
class ModelResult:
    """Validation results for one model."""

    name: str
    n_parameters: int
    val_loss: float
    val_accuracy: float
    epochs_run: int
    confusion: np.ndarray
    recall: np.ndarray


class DigitRows(Dataset[tuple[torch.Tensor, int]]):
    """Digit images as (1, 8, 8) float32 tensors, shifted at random when augment is on."""

    def __init__(
        self, images: np.ndarray, labels: np.ndarray, augment: bool, max_shift: int, seed: int
    ) -> None:
        """Keep the images and a seeded generator for the shifts."""
        self.images, self.labels = images, labels
        self.augment, self.max_shift = augment, max_shift
        self.rng = np.random.default_rng(seed)

    def __len__(self) -> int:
        """Number of images."""
        return len(self.labels)

    def __getitem__(self, i: int) -> tuple[torch.Tensor, int]:
        """Image i, shifted when augmenting, with its label."""
        image = self.images[i]
        if self.augment:
            image = random_shift(image, self.max_shift, self.rng)
        return torch.as_tensor(add_channel(image[None])[0]), int(self.labels[i])


def make_dense(n_classes: int) -> nn.Module:
    """The comparison model: flattened pixels, one hidden layer of 64 (module B23)."""
    return nn.Sequential(nn.Flatten(), nn.Linear(64, 64), nn.ReLU(), nn.Linear(64, n_classes))


def evaluate(
    model: nn.Module, loader: DataLoader[tuple[torch.Tensor, int]]
) -> tuple[float, np.ndarray]:
    """Mean cross-entropy and predicted classes, in eval mode without gradients."""
    model.eval()
    loss_fn = nn.CrossEntropyLoss(reduction="sum")
    total, rows, preds = 0.0, 0, []
    with torch.no_grad():
        for x, y in loader:
            logits = model(x)
            total += loss_fn(logits, y).item()
            rows += len(y)
            preds.append(logits.argmax(dim=1).numpy())
    return total / rows, np.concatenate(preds)


def fit_model(
    name: str,
    model: nn.Module,
    train_loader: DataLoader[tuple[torch.Tensor, int]],
    val_loader: DataLoader[tuple[torch.Tensor, int]],
    y_val: np.ndarray,
    config: TrainConfig,
) -> ModelResult:
    """Train with AdamW and early stopping on validation loss, then score the best weights."""
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.lr)
    loss_fn = nn.CrossEntropyLoss()
    best_loss, best_state, bad, epochs = math.inf, copy.deepcopy(model.state_dict()), 0, 0
    for _ in range(config.max_epochs):
        model.train()
        for x, y in train_loader:
            optimizer.zero_grad()
            loss_fn(model(x), y).backward()
            optimizer.step()
        epochs += 1
        val_loss, _ = evaluate(model, val_loader)
        if val_loss < best_loss - 1e-4:
            best_loss, best_state, bad = val_loss, copy.deepcopy(model.state_dict()), 0
        else:
            bad += 1
            if bad >= config.patience:
                break
    model.load_state_dict(best_state)
    val_loss, preds = evaluate(model, val_loader)
    cm = confusion(y_val, preds, N_CLASSES)
    return ModelResult(
        name=name,
        n_parameters=sum(p.numel() for p in model.parameters()),
        val_loss=val_loss,
        val_accuracy=float((preds == y_val).mean()),
        epochs_run=epochs,
        confusion=cm,
        recall=recall_by_class(cm),
    )


def run(config: TrainConfig) -> list[ModelResult]:
    """Train the dense network and the CNN on the same split and the same batches."""
    images, labels = load_digit_images()
    idx_train, idx_val = train_test_split(
        np.arange(len(labels)),
        test_size=config.val_share,
        stratify=labels,
        random_state=config.seed,
    )
    val_loader = DataLoader(
        DigitRows(images[idx_val], labels[idx_val], False, 0, config.seed), batch_size=512
    )
    results = []
    for name, build in [("dense", make_dense), ("cnn", make_cnn)]:
        torch.manual_seed(config.seed)
        train_rows = DigitRows(
            images[idx_train], labels[idx_train], config.augment, config.max_shift, config.seed
        )
        train_loader = DataLoader(
            train_rows,
            batch_size=config.batch_size,
            shuffle=True,
            generator=torch.Generator().manual_seed(config.seed),
        )
        model = build(N_CLASSES)
        results.append(fit_model(name, model, train_loader, val_loader, labels[idx_val], config))
    return results
