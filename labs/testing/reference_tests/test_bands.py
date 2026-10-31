"""Lesson B19-L3: one row per case, both sides of every threshold."""

from __future__ import annotations

import pytest
from survey_stats.bands import age_band


@pytest.mark.parametrize(
    ("age", "expected"),
    [
        pytest.param(16, "16-34", id="youngest"),
        pytest.param(34, "16-34", id="below-35"),
        pytest.param(35, "35-54", id="at-35"),
        pytest.param(54, "35-54", id="below-55"),
        pytest.param(55, "55+", id="at-55"),
        pytest.param(None, None, id="missing"),
    ],
)
def test_age_band(age: int | None, expected: str | None) -> None:
    assert age_band(age) == expected
