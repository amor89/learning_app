"""Age bands for reporting."""

from __future__ import annotations


def age_band(age: int | None) -> str | None:
    """Return the reporting band for an age.

    Args:
        age: Age in years, or None when missing.

    Returns:
        "16-34" under 35, "35-54" under 55, "55+" from 55, or None for a missing age.
    """
    if age is None:
        return None
    if age < 35:
        return "16-34"
    if age < 55:
        return "35-54"
    return "55+"
