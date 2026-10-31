"""Lessons B19-L1, L2 and L4: errors, fixtures and frame comparisons."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd
import pytest
from survey_stats.weights import cap_weights, effective_n, in_scope_weight, normalise


def test_normalise_sums_to_one() -> None:
    assert normalise([1.0, 3.0]) == pytest.approx([0.25, 0.75])


def test_normalise_rejects_negative_weight() -> None:
    with pytest.raises(ValueError, match="negative weight"):
        normalise([2.0, -1.0])


def test_normalise_rejects_zero_total() -> None:
    with pytest.raises(ValueError, match="total weight is 0"):
        normalise([0.0, 0.0])


def test_cap_weights_caps_and_keeps_input(make_respondents: Callable[..., pd.DataFrame]) -> None:
    df = make_respondents([1.0, 3.0, np.nan])
    before = df.copy()

    result = cap_weights(df, cap=2.0)

    expected = make_respondents([1.0, 2.0, np.nan])
    pd.testing.assert_frame_equal(result, expected)
    pd.testing.assert_frame_equal(df, before)


def test_cap_weights_rejects_cap_below_one(make_respondents: Callable[..., pd.DataFrame]) -> None:
    with pytest.raises(ValueError, match="cap must be at least"):
        cap_weights(make_respondents([1.0]), cap=0.5)


def test_in_scope_weight_skips_out_of_scope(
    make_respondents: Callable[..., pd.DataFrame],
) -> None:
    df = make_respondents([1.0, 3.0], in_scope=[True, False])
    assert in_scope_weight(df) == 1.0


@pytest.mark.parametrize(
    ("weights", "expected"),
    [
        pytest.param([1.0, 1.0, 1.0, 1.0], 4.0, id="equal-weights"),
        pytest.param([1.0, 3.0], 1.6, id="unequal-weights"),
    ],
)
def test_effective_n(weights: list[float], expected: float) -> None:
    assert effective_n(weights) == pytest.approx(expected)


def test_effective_n_all_zero_is_none() -> None:
    assert effective_n([0.0, 0.0]) is None
