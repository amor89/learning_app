"""The full comparison. Skipped when PyTorch is missing."""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from finetune_lab.train import (  # noqa: E402
    FinetuneConfig,
    ModelConfig,
    PretrainConfig,
    finetune,
    pretrain,
)


def test_pretraining_helps_with_few_labels() -> None:
    state, losses = pretrain(PretrainConfig(), ModelConfig())
    assert losses[-1] < 0.7 < losses[0]
    results = {
        s: finetune(FinetuneConfig(strategy=s), ModelConfig(), state)
        for s in ("scratch", "head", "full", "lora")
    }
    assert results["full"].accuracy >= 0.95
    assert results["lora"].accuracy >= 0.9
    assert results["scratch"].accuracy <= 0.85
    assert results["lora"].trainable < 0.05 * results["full"].trainable
