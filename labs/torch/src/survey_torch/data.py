"""A seeded generator of synthetic survey data with a binary outcome.

The outcome, "would recommend", depends on satisfaction thresholds, tenure,
price and region, on an interaction between contact and satisfaction, and on
an interaction between age and price. A linear model misses the interactions, so a small
network has something to learn that the baseline cannot.
"""

from __future__ import annotations

import numpy as np

FEATURES = [
    "age",
    "tenure_years",
    "satisfaction",
    "price_index",
    "contacted",
    "region_north",
    "region_south",
    "region_east",
    "region_west",
]
REGION_EFFECT = np.array([0.0, 0.3, -0.2, 0.1])
SIGNAL_SCALE = 3.0


def make_survey_data(n: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Features and a 0/1 target for n synthetic respondents.

    Args:
        n: Number of respondents.
        seed: Seed for the generator, so the data is the same every run.

    Returns:
        X with one column per name in FEATURES (float64), and y of 0 and 1 (int64).

    Raises:
        ValueError: If n is below 1.
    """
    if n < 1:
        raise ValueError(f"n must be at least 1, got {n}")
    rng = np.random.default_rng(seed)
    age = rng.uniform(18, 80, n)
    tenure = np.minimum(rng.exponential(3.0, n), 20.0)
    satisfaction = rng.integers(0, 11, n).astype(float)
    price = rng.normal(100.0, 15.0, n)
    contacted = (rng.random(n) < 0.3).astype(float)
    region = rng.integers(0, 4, n)
    signal = (
        -0.6
        + 1.0 * (satisfaction >= 8)
        - 1.0 * (satisfaction <= 3)
        + 1.2 * contacted * (satisfaction >= 6)
        - 1.5 * (age < 30) * (price > 105)
        + 0.03 * tenure
        - 0.02 * (price - 100)
    )
    logit = SIGNAL_SCALE * signal + REGION_EFFECT[region]
    y = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(np.int64)
    regions = np.eye(4)[region]
    X = np.column_stack([age, tenure, satisfaction, price, contacted, regions])
    return X, y
