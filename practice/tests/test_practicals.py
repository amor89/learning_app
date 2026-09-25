"""Run the code cells of every Databricks practical notebook on a local SparkSession.

Databricks-only helpers are stubbed: display() prints a few rows. A practical that
fails here would fail for the learner in Databricks Free Edition too.
"""

from __future__ import annotations

import sys
import types
from typing import Any

import pytest
from pyspark.sql import DataFrame, SparkSession

from learnkit.loader import load_course

NOTEBOOKS = [
    (lesson.id, [c.source for c in lesson.practical.cells if c.kind == "code"])
    for lesson in load_course().lessons()
    if lesson.practical is not None and lesson.practical.platform == "databricks"
]


def fake_display(obj: Any) -> None:
    """Stand-in for the Databricks display() helper."""
    if isinstance(obj, DataFrame):
        obj.show(5, truncate=False)
    else:
        print(obj)


@pytest.mark.parametrize(("lesson_id", "cells"), NOTEBOOKS, ids=[n[0] for n in NOTEBOOKS])
def test_practical_runs(spark: SparkSession, lesson_id: str, cells: list[str]) -> None:
    module = types.ModuleType(f"practical_{lesson_id.replace('-', '_')}")
    sys.modules[module.__name__] = module
    namespace: dict[str, Any] = module.__dict__
    namespace.update({"spark": spark, "display": fake_display})
    try:
        for cell in cells:
            exec(cell, namespace)
    finally:
        sys.modules.pop(module.__name__, None)
