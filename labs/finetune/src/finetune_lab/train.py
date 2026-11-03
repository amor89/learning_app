"""Pretrain with masked tokens, then fine-tune four ways and compare."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import torch
from torch import nn

from finetune_lab.data import LENGTH, MASK, STEPS, VOCAB_SIZE, make_sequences
from finetune_lab.lora import add_lora
from finetune_lab.model import Classifier, Encoder, MaskedLM
from finetune_lab.schedule import warmup_linear
from finetune_lab.strategies import count_parameters, load_backbone, set_trainable

Strategy = Literal["scratch", "head", "full", "lora"]
STRATEGIES: tuple[Strategy, ...] = ("scratch", "head", "full", "lora")
IGNORE = -100


@dataclass(frozen=True)
class ModelConfig:
    """Encoder size, shared by pretraining and fine-tuning."""

    d: int = 32
    heads: int = 4
    n_layers: int = 2


@dataclass(frozen=True)
class PretrainConfig:
    """Settings for masked-token pretraining."""

    seed: int = 0
    n_sequences: int = 20_000
    mask_rate: float = 0.15
    lr: float = 3e-3
    batch_size: int = 128
    epochs: int = 8


@dataclass(frozen=True)
class FinetuneConfig:
    """Settings for one fine-tuning run."""

    strategy: Strategy = "full"
    seed: int = 0
    n_train: int = 60
    n_val: int = 2_000
    epochs: int = 60
    batch_size: int = 16
    warmup_share: float = 0.1
    lora_r: int = 4
    lora_alpha: float = 8.0

    @property
    def lr(self) -> float:
        """A smaller rate when every pretrained weight moves."""
        return 1e-3 if self.strategy == "full" else 3e-3


@dataclass(frozen=True)
class FinetuneResult:
    """Validation accuracy and parameter counts of one run."""

    strategy: Strategy
    seed: int
    accuracy: float
    trainable: int
    total: int


def mask_tokens(
    ids: torch.Tensor, rate: float, generator: torch.Generator
) -> tuple[torch.Tensor, torch.Tensor]:
    """Replace a random share of tokens with MASK.

    Returns:
        Inputs with MASK at the chosen positions, and targets holding the original
        token there and IGNORE elsewhere, so the loss counts masked positions only.
    """
    chosen = torch.rand(ids.shape, generator=generator) < rate
    return ids.masked_fill(chosen, MASK), ids.masked_fill(~chosen, IGNORE)


def pretrain(
    config: PretrainConfig, model_config: ModelConfig
) -> tuple[dict[str, torch.Tensor], list[float]]:
    """Train a MaskedLM on unlabelled sequences.

    Returns:
        The model's state_dict, keys `encoder.*` and `head.*`, and the loss per epoch.
    """
    torch.manual_seed(config.seed)
    ids = torch.as_tensor(make_sequences(config.n_sequences, 100 + config.seed)[0])
    mc = model_config
    model = MaskedLM(Encoder(VOCAB_SIZE, mc.d, mc.heads, mc.n_layers, LENGTH), mc.d, VOCAB_SIZE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.lr)
    gen = torch.Generator().manual_seed(config.seed)
    losses: list[float] = []
    for _ in range(config.epochs):
        model.train()
        total, batches = 0.0, 0
        for batch in torch.randperm(len(ids), generator=gen).split(config.batch_size):
            inputs, targets = mask_tokens(ids[batch], config.mask_rate, gen)
            logits = model(inputs)
            loss = nn.functional.cross_entropy(
                logits.reshape(-1, VOCAB_SIZE), targets.reshape(-1), ignore_index=IGNORE
            )
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total, batches = total + loss.item(), batches + 1
        losses.append(total / batches)
    return model.state_dict(), losses


def build(
    config: FinetuneConfig, model_config: ModelConfig, checkpoint: dict[str, torch.Tensor]
) -> Classifier:
    """A classifier set up for one strategy.

    scratch: random encoder, all trainable. head: pretrained encoder frozen, new
    head trained. full: pretrained encoder and head all trained. lora: pretrained
    encoder frozen, LoRA on queries and values, head trained.
    """
    torch.manual_seed(config.seed)
    mc = model_config
    model = Classifier(Encoder(VOCAB_SIZE, mc.d, mc.heads, mc.n_layers, LENGTH), mc.d, len(STEPS))
    if config.strategy != "scratch":
        load_backbone(model, checkpoint)
    if config.strategy in ("scratch", "full"):
        set_trainable(model, ("",))
    else:
        set_trainable(model, ("head.",))
    if config.strategy == "lora":
        add_lora(model, config.lora_r, config.lora_alpha)
    return model


def accuracy(model: nn.Module, ids: torch.Tensor, labels: torch.Tensor) -> float:
    """Share of sequences classified correctly, in eval mode without gradients."""
    model.eval()
    with torch.no_grad():
        preds = model(ids).argmax(dim=1)
    return float((preds == labels).float().mean())


def finetune(
    config: FinetuneConfig, model_config: ModelConfig, checkpoint: dict[str, torch.Tensor]
) -> FinetuneResult:
    """Fine-tune on n_train labelled sequences with warm-up and linear decay, then score."""
    model = build(config, model_config, checkpoint)
    train_ids, train_labels = (
        torch.as_tensor(a) for a in make_sequences(config.n_train, 7 + config.seed)
    )
    val_ids, val_labels = (torch.as_tensor(a) for a in make_sequences(config.n_val, 999))
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(params, lr=config.lr)
    steps_per_epoch = -(-config.n_train // config.batch_size)
    total_steps = steps_per_epoch * config.epochs
    warmup = int(config.warmup_share * total_steps)
    scheduler = torch.optim.lr_scheduler.LambdaLR(
        optimizer, lambda step: warmup_linear(min(step, total_steps), warmup, total_steps)
    )
    gen = torch.Generator().manual_seed(config.seed)
    for _ in range(config.epochs):
        model.train()
        for batch in torch.randperm(config.n_train, generator=gen).split(config.batch_size):
            loss = nn.functional.cross_entropy(model(train_ids[batch]), train_labels[batch])
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            scheduler.step()
    trainable, total = count_parameters(model)
    return FinetuneResult(
        config.strategy, config.seed, accuracy(model, val_ids, val_labels), trainable, total
    )


def save_checkpoint(state: dict[str, torch.Tensor], path: Path) -> None:
    """Save a state_dict with torch.save."""
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(state, path)


def load_checkpoint(path: Path) -> dict[str, torch.Tensor]:
    """Load a state_dict. weights_only=True refuses anything but tensors and plain containers."""
    state: dict[str, torch.Tensor] = torch.load(path, weights_only=True)
    return state
