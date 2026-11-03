"""What layers.py must do. Skipped when PyTorch is missing."""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

import torch.nn.functional as F  # noqa: E402
from tiny_transformer.layers import (  # noqa: E402
    Block,
    MultiHeadSelfAttention,
    attention,
    sinusoidal_positions,
)


@pytest.fixture
def qkv() -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    gen = torch.Generator().manual_seed(0)
    return tuple(torch.randn(2, 3, 5, 8, generator=gen) for _ in range(3))  # type: ignore[return-value]


# attention (lessons B25-L3 and B25-L4) --------------------------------------


def test_attention_matches_pytorch(qkv: tuple[torch.Tensor, ...]) -> None:
    q, k, v = qkv
    assert torch.allclose(attention(q, k, v), F.scaled_dot_product_attention(q, k, v), atol=1e-5)


def test_attention_causal_mask_matches_is_causal(qkv: tuple[torch.Tensor, ...]) -> None:
    q, k, v = qkv
    allowed = torch.ones(5, 5, dtype=torch.bool).tril()
    expected = F.scaled_dot_product_attention(q, k, v, is_causal=True)
    assert torch.allclose(attention(q, k, v, allowed), expected, atol=1e-5)


def test_attention_ignores_disallowed_keys(qkv: tuple[torch.Tensor, ...]) -> None:
    q, k, v = qkv
    allowed = torch.tensor([True, True, True, False, False])
    changed = v.clone()
    changed[..., 3:, :] += 100.0
    assert torch.allclose(attention(q, k, v, allowed), attention(q, k, changed, allowed), atol=1e-5)


# sinusoidal_positions (lesson B25-L5) ----------------------------------------


def test_sinusoidal_values() -> None:
    expected = torch.tensor(
        [[0.0, 1.0, 0.0, 1.0], [0.8415, 0.5403, 0.01, 1.0], [0.9093, -0.4161, 0.02, 0.9998]]
    )
    assert torch.allclose(sinusoidal_positions(3, 4), expected, atol=1e-4)
    with pytest.raises(ValueError):
        sinusoidal_positions(3, 5)


# MultiHeadSelfAttention and Block (lessons B25-L5 and B25-L6) ------------------


def test_multi_head_shape_parameters_and_guard() -> None:
    layer = MultiHeadSelfAttention(16, 4)
    x = torch.randn(2, 6, 16)
    assert layer(x, torch.zeros(2, 6, dtype=torch.bool)).shape == (2, 6, 16)
    assert sum(p.numel() for p in layer.parameters()) == 4 * 16 * 16 + 4 * 16
    with pytest.raises(ValueError):
        MultiHeadSelfAttention(10, 3)


@pytest.mark.parametrize("layer_type", [MultiHeadSelfAttention, Block])
def test_padding_cannot_change_real_positions(layer_type: type) -> None:
    torch.manual_seed(0)
    layer = layer_type(16, 4).eval()
    x = torch.randn(2, 6, 16)
    is_pad = torch.tensor([[False] * 4 + [True] * 2, [False] * 6])
    changed = x.clone()
    changed[0, 4:] += 50.0
    a, b = layer(x, is_pad), layer(changed, is_pad)
    assert torch.allclose(a[0, :4], b[0, :4], atol=1e-5)
    assert torch.allclose(a[1], b[1], atol=1e-5)


def test_block_is_residual_and_pre_norm() -> None:
    block = Block(16, 4)
    assert isinstance(block.norm_1, torch.nn.LayerNorm) and isinstance(
        block.norm_2, torch.nn.LayerNorm
    )
    with torch.no_grad():
        for p in block.attn.out.parameters():
            p.zero_()
        block.ff[-1].weight.zero_()
        block.ff[-1].bias.zero_()
    x = torch.randn(2, 5, 16)
    assert torch.allclose(block(x, torch.zeros(2, 5, dtype=torch.bool)), x)
