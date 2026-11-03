"""Synthetic open survey answers about price, delivery or staff.

`shifted=True` makes a later batch: answers get longer, delivery complaints
become more common, and new words about an app appear. A drift check should
notice.
"""

from __future__ import annotations

import numpy as np

TOPICS = ("price", "delivery", "staff")
WORDS = {
    "price": ["expensive", "price", "cost", "cheap", "discount", "value", "money", "offer"],
    "delivery": ["late", "delivery", "parcel", "courier", "arrived", "tracking", "slow", "box"],
    "staff": ["staff", "rude", "helpful", "friendly", "manager", "service", "polite", "team"],
}
FILLER = ["the", "was", "very", "and", "it", "my", "a", "really", "quite", "not"]
NEW_WORDS = ["app", "checkout", "crashed", "login", "update", "screen"]


def make_answers(n: int, seed: int, shifted: bool = False) -> tuple[list[str], list[str]]:
    """Answers and their topic labels.

    Args:
        n: Number of answers.
        seed: Seed for the generator.
        shifted: Produce a later, drifted batch.

    Returns:
        (texts, labels), each of length n.

    Raises:
        ValueError: If n is below 1.
    """
    if n < 1:
        raise ValueError(f"n must be at least 1, got {n}")
    rng = np.random.default_rng(seed)
    mix = [0.2, 0.6, 0.2] if shifted else [1 / 3, 1 / 3, 1 / 3]
    texts: list[str] = []
    labels: list[str] = []
    for _ in range(n):
        topic = TOPICS[int(rng.choice(len(TOPICS), p=mix))]
        length = int(rng.integers(8, 20)) if shifted else int(rng.integers(4, 12))
        words = []
        for _ in range(length):
            draw = rng.random()
            if draw < 0.4:
                pool = WORDS[topic]
            elif shifted and draw < 0.55:
                pool = NEW_WORDS
            else:
                pool = FILLER
            words.append(pool[int(rng.integers(len(pool)))])
        texts.append(" ".join(words))
        labels.append(topic)
    return texts, labels
