"""Train the classifier on the synthetic task and report validation accuracy."""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn

from tiny_transformer.data import MAX_LEN, N_TOKENS, make_sequences
from tiny_transformer.model import Classifier


@dataclass(frozen=True)
class TrainConfig:
    """Every setting of one run."""

    seed: int = 0
    n_train: int = 4000
    n_val: int = 1000
    d: int = 32
    heads: int = 4
    n_layers: int = 2
    lr: float = 3e-3
    batch_size: int = 64
    epochs: int = 30
    use_positions: bool = True


@dataclass(frozen=True)
class RunResult:
    """Validation accuracy after training, and the training loss per epoch."""

    val_accuracy: float
    losses: list[float]


def accuracy(model: nn.Module, ids: torch.Tensor, labels: torch.Tensor) -> float:
    """Share of sequences classified correctly, in eval mode without gradients."""
    model.eval()
    with torch.no_grad():
        preds = model(ids).argmax(dim=1)
    return float((preds == labels).float().mean())


def run(config: TrainConfig) -> RunResult:
    """Train with AdamW and cross-entropy, then score on fresh validation sequences."""
    torch.manual_seed(config.seed)
    train_ids, train_labels = (
        torch.as_tensor(a) for a in make_sequences(config.n_train, config.seed)
    )
    val_ids, val_labels = (
        torch.as_tensor(a) for a in make_sequences(config.n_val, config.seed + 1)
    )
    model = Classifier(
        N_TOKENS + 1, config.d, config.heads, config.n_layers, MAX_LEN, config.use_positions
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.lr)
    loss_fn = nn.CrossEntropyLoss()
    order_gen = torch.Generator().manual_seed(config.seed)
    losses: list[float] = []
    for _ in range(config.epochs):
        model.train()
        total = 0.0
        for batch in torch.randperm(config.n_train, generator=order_gen).split(config.batch_size):
            optimizer.zero_grad()
            loss = loss_fn(model(train_ids[batch]), train_labels[batch])
            loss.backward()
            optimizer.step()
            total += loss.item() * len(batch)
        losses.append(total / config.n_train)
    return RunResult(accuracy(model, val_ids, val_labels), losses)
