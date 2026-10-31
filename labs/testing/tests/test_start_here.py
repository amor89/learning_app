"""Your tests go in this folder. This one shows that the setup works."""

from survey_stats.bands import age_band


def test_setup_works() -> None:
    assert age_band(40) == "35-54"
