"""What drift.py must do, and checks on the given data and model. No MLflow or FastAPI needed."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest
from serve_lab.data import make_answers
from serve_lab.drift import drift_status, psi
from serve_lab.model import ModelMeta, load_artifact, save_artifact, train


def test_psi_is_zero_for_the_same_distribution() -> None:
    values = np.random.default_rng(0).normal(size=5_000)
    assert psi(values, values) == pytest.approx(0.0, abs=1e-9)


def test_psi_matches_the_formula_on_two_bins() -> None:
    expected = np.array([1.0, 2.0, 3.0, 4.0])
    actual = np.array([1.0, 3.5, 4.0, 4.0])
    want = (0.25 - 0.5) * math.log(0.25 / 0.5) + (0.75 - 0.5) * math.log(0.75 / 0.5)
    assert psi(expected, actual, bins=2) == pytest.approx(want)


def test_psi_grows_with_the_shift_and_handles_empty_bins() -> None:
    rng = np.random.default_rng(1)
    base = rng.normal(size=5_000)
    small, large = psi(base, rng.normal(0.2, 1.0, 5_000)), psi(base, rng.normal(1.0, 1.0, 5_000))
    assert 0.0 < small < 0.1 < 0.25 < large
    assert math.isfinite(psi(base, np.full(100, 10.0)))


def test_psi_guards() -> None:
    with pytest.raises(ValueError):
        psi(np.array([1.0, 2.0]), np.array([1.0]), bins=1)
    with pytest.raises(ValueError):
        psi(np.array([]), np.array([1.0]))


@pytest.mark.parametrize(
    ("value", "status"), [(0.0, "stable"), (0.0999, "stable"), (0.1, "warn"), (0.25, "alert")]
)
def test_drift_status_bands(value: float, status: str) -> None:
    assert drift_status(value) == status


def test_drift_status_guards() -> None:
    with pytest.raises(ValueError):
        drift_status(-0.1)
    with pytest.raises(ValueError):
        drift_status(0.1, warn=0.3, alert=0.2)


def test_data_and_model(tmp_path: Path) -> None:
    texts, labels = make_answers(30, seed=0)
    assert len(texts) == len(labels) == 30 and set(labels) <= {"price", "delivery", "staff"}
    model, accuracy = train()
    assert accuracy >= 0.9
    save_artifact(model, ModelMeta("survey_topics", "3"), tmp_path)
    loaded, meta = load_artifact(tmp_path)
    assert meta == ModelMeta("survey_topics", "3")
    assert list(loaded.predict(texts[:5])) == list(model.predict(texts[:5]))
