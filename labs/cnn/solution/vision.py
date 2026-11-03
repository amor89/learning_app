"""Reference solutions for src/digits_cnn/vision.py.

Read this only after your own version passes the tests. The repository's CI
copies this file over the stubs and runs the lab's tests.
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
    if images.ndim != 3 or len(images) == 0:
        raise ValueError(f"expected (N, H, W) with N >= 1, got {images.shape}")
    return images[:, None, :, :].astype(np.float32)


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
    if image.ndim != 2 or max_shift < 0:
        raise ValueError(f"need a 2-D image and max_shift >= 0, got {image.shape}, {max_shift}")
    h, w = image.shape
    padded = np.pad(image, max_shift)
    top, left = rng.integers(0, 2 * max_shift + 1, size=2)
    result: np.ndarray = padded[top : top + h, left : left + w]
    return result


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
    if len(y_true) != len(y_pred):
        raise ValueError(f"{len(y_true)} true labels and {len(y_pred)} predictions")
    labels = np.concatenate([y_true, y_pred])
    if len(labels) and (labels.min() < 0 or labels.max() >= n_classes):
        raise ValueError(f"labels must lie in 0 to {n_classes - 1}")
    cm = np.zeros((n_classes, n_classes), dtype=np.int64)
    for t, p in zip(y_true, y_pred, strict=True):
        cm[t, p] += 1
    return cm


def recall_by_class(cm: np.ndarray) -> np.ndarray:
    """Recall per class, NaN where a class has no true examples (lesson B24-L6).

    Raises:
        ValueError: If cm is not square.
    """
    if cm.ndim != 2 or cm.shape[0] != cm.shape[1]:
        raise ValueError(f"need a square matrix, got {cm.shape}")
    totals = cm.sum(axis=1)
    result: np.ndarray = np.where(totals > 0, cm.diagonal() / np.maximum(totals, 1), np.nan)
    return result
