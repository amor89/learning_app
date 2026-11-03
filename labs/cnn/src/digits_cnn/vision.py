"""Image steps you write: channels, augmentation and evaluation. NumPy only.

Each function raises NotImplementedError until you fill it in.
tests/test_vision.py says what each must do. None of this needs PyTorch.
"""

from __future__ import annotations

import numpy as np


def add_channel(images: np.ndarray) -> np.ndarray:
    """Greyscale images (N, H, W) as a float32 batch (N, 1, H, W) (lessons B24-L2 and B24-L4).

    Args:
        images: Images with values in [0, 1].

    Returns:
        A float32 array with a channel dimension of size 1 at position 1.

    Raises:
        ValueError: If images is not 3-D or holds no images.
    """
    raise NotImplementedError("add_channel")


def random_shift(image: np.ndarray, max_shift: int, rng: np.random.Generator) -> np.ndarray:
    """Shift a 2-D image by up to max_shift pixels, filling with zeros (lesson B24-L4).

    Args:
        image: 2-D image.
        max_shift: Largest shift in any direction.
        rng: Seeded generator. One draw of two integers per call.

    Returns:
        An array with the image's shape.

    Raises:
        ValueError: If image is not 2-D or max_shift is negative.
    """
    raise NotImplementedError("random_shift")


def confusion(y_true: np.ndarray, y_pred: np.ndarray, n_classes: int) -> np.ndarray:
    """Confusion matrix, true classes in rows (lesson B24-L6).

    Args:
        y_true: True class indices.
        y_pred: Predicted class indices.
        n_classes: Number of classes.

    Returns:
        Integer counts, shape (n_classes, n_classes).

    Raises:
        ValueError: If the lengths differ or a label is out of range.
    """
    raise NotImplementedError("confusion")


def recall_by_class(cm: np.ndarray) -> np.ndarray:
    """Recall per class, NaN where a class has no true examples (lesson B24-L6).

    Raises:
        ValueError: If cm is not square.
    """
    raise NotImplementedError("recall_by_class")
