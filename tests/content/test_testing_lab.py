"""The B19 testing lab's reference suite passes with full branch coverage.

The lab sheet tells learners to compare their suite with reference_tests/, so the
reference must stay green and must reach every branch of the lab package.
"""

import subprocess
import sys
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parents[2] / "labs" / "testing"


def test_reference_suite_covers_every_branch() -> None:
    """Run the reference suite in its own pytest process, as the lab sheet does."""
    pytest.importorskip("pytest_cov")
    pytest.importorskip("statsmodels")
    command = [
        sys.executable,
        "-m",
        "pytest",
        "reference_tests",
        "-q",
        "-p",
        "no:cacheprovider",
        "--cov=survey_stats",
        "--cov-branch",
        "--cov-fail-under=100",
    ]
    result = subprocess.run(command, cwd=LAB, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]


def test_starter_suite_passes() -> None:
    """The one example test in tests/ shows a learner that the setup works."""
    command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    result = subprocess.run(command, cwd=LAB, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
