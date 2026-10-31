"""Confidence intervals for proportions."""

from __future__ import annotations

import math

Z_95 = 1.959964


def wilson_interval(successes: int, n: int, z: float = Z_95) -> tuple[float, float]:
    """Wilson score interval for a proportion.

    Args:
        successes: Number of successes, from 0 to n.
        n: Sample size, above 0.
        z: Normal quantile for the confidence level.

    Returns:
        (lower, upper), clipped to [0, 1].

    Raises:
        ValueError: If n is not positive or successes is outside 0 to n.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    if not 0 <= successes <= n:
        raise ValueError("successes must be between 0 and n")
    p = successes / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z / denom * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return max(0.0, centre - half), min(1.0, centre + half)
