"""Lesson B19-L5: an oracle, a seed and a tolerance from theory."""

from __future__ import annotations

import math

import numpy as np
import pytest
from statsmodels.stats.proportion import proportion_confint
from survey_stats.intervals import wilson_interval


def test_matches_statsmodels() -> None:
    expected = proportion_confint(12, 40, alpha=0.05, method="wilson")
    np.testing.assert_allclose(wilson_interval(12, 40), expected, rtol=1e-6)


@pytest.mark.parametrize(("successes", "n"), [(0, 20), (20, 20)])
def test_bounds_stay_in_unit_interval(successes: int, n: int) -> None:
    lower, upper = wilson_interval(successes, n)
    assert 0.0 <= lower <= successes / n <= upper <= 1.0


@pytest.mark.parametrize(("successes", "n"), [(1, 0), (-1, 10), (11, 10)])
def test_rejects_impossible_counts(successes: int, n: int) -> None:
    with pytest.raises(ValueError):
        wilson_interval(successes, n)


@pytest.mark.slow
def test_coverage_close_to_95_percent(rng: np.random.Generator) -> None:
    sims, p, n = 2000, 0.05, 30
    counts = rng.binomial(n, p, size=sims)
    covered = [lo <= p <= hi for lo, hi in (wilson_interval(int(c), n) for c in counts)]
    se = math.sqrt(0.95 * 0.05 / sims)
    assert abs(float(np.mean(covered)) - 0.95) < 4 * se
