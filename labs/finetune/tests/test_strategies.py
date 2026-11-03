"""What strategies.py and lora.py must do. Skipped when PyTorch is missing."""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from finetune_lab.lora import LoRALinear, add_lora  # noqa: E402
from finetune_lab.model import Classifier, Encoder, MaskedLM  # noqa: E402
from finetune_lab.strategies import count_parameters, load_backbone, set_trainable  # noqa: E402
from torch import nn  # noqa: E402


def _pretrained() -> dict[str, torch.Tensor]:
    torch.manual_seed(0)
    return MaskedLM(Encoder(12, 16, 4, 1, 12), 16, 12).state_dict()


def _classifier() -> Classifier:
    torch.manual_seed(1)
    return Classifier(Encoder(12, 16, 4, 1, 12), 16, 3)


def test_load_backbone_copies_encoder_and_reports_new_head() -> None:
    state, model = _pretrained(), _classifier()
    missing = load_backbone(model, state)
    assert missing == ["head.bias", "head.weight"]
    assert torch.equal(model.encoder.tokens.weight, state["encoder.tokens.weight"])


def test_load_backbone_rejects_wrong_prefix() -> None:
    state = {"model." + k: v for k, v in _pretrained().items()}
    with pytest.raises(ValueError):
        load_backbone(_classifier(), state)


def test_load_backbone_rejects_partial_encoder() -> None:
    state = {k: v for k, v in _pretrained().items() if "blocks" not in k}
    with pytest.raises(ValueError):
        load_backbone(_classifier(), state)


def test_set_trainable_head_only() -> None:
    model = _classifier()
    assert set_trainable(model, ("head.",)) == 16 * 3 + 3
    assert not model.encoder.tokens.weight.requires_grad and model.head.weight.requires_grad
    assert set_trainable(model, ("",)) == count_parameters(model)[1]


def test_lora_starts_equal_and_counts() -> None:
    torch.manual_seed(0)
    base = nn.Linear(8, 6)
    layer = LoRALinear(base, r=2, alpha=4)
    x = torch.randn(5, 8)
    assert torch.allclose(layer(x), base(x))
    assert layer.A.shape == (2, 8) and layer.B.shape == (6, 2) and layer.scaling == 2.0
    assert not base.weight.requires_grad and layer.A.requires_grad and layer.B.requires_grad
    with pytest.raises(ValueError):
        LoRALinear(nn.Linear(8, 6), r=0, alpha=1)


def test_lora_update_and_merge() -> None:
    torch.manual_seed(0)
    layer = LoRALinear(nn.Linear(8, 6), r=2, alpha=4)
    with torch.no_grad():
        layer.B.normal_()
    x = torch.randn(5, 8)
    expected = layer.base(x) + 2.0 * x @ layer.A.T @ layer.B.T
    assert torch.allclose(layer(x), expected, atol=1e-6)
    merged = layer.merged()
    assert isinstance(merged, nn.Linear)
    assert torch.allclose(merged(x), layer(x), atol=1e-5)


def test_add_lora_wraps_queries_and_values() -> None:
    model = _classifier()
    set_trainable(model, ("head.",))
    x = torch.randint(1, 11, (4, 12))
    model.eval()
    before = model(x)
    assert add_lora(model, r=2, alpha=4) == 2
    attn = model.encoder.blocks[0].attn
    assert isinstance(attn.q, LoRALinear) and isinstance(attn.v, LoRALinear)
    assert not isinstance(attn.k, LoRALinear)
    assert torch.allclose(model(x), before, atol=1e-6)
    trainable, _ = count_parameters(model)
    assert trainable == 51 + 2 * 2 * (16 + 16)
