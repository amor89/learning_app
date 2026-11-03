"""Load scikit-learn's bundled digits as images in [0, 1]. Nothing downloads."""

from __future__ import annotations

import numpy as np
from sklearn.datasets import load_digits

N_CLASSES = 10
PIXEL_MAX = 16.0


def load_digit_images() -> tuple[np.ndarray, np.ndarray]:
    """The 1,797 digits as (N, 8, 8) float images in [0, 1] and int64 labels 0 to 9.

    Returns:
        Images scaled by the dataset's maximum pixel value, 16, and the labels.
    """
    digits = load_digits()
    images = np.asarray(digits.images, dtype=np.float64) / PIXEL_MAX
    labels = np.asarray(digits.target, dtype=np.int64)
    return images, labels
