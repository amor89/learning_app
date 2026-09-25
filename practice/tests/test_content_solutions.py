"""Run every PySpark reference solution from the lesson content on a local SparkSession.

The browser checks PySpark answers statically. This test proves that each reference
solution also behaves correctly on real Spark 4.0 with Delta Lake.
"""

from __future__ import annotations

import sys
import types
from typing import Any

import pytest
from pyspark.sql import SparkSession

from learnkit.loader import load_course
from learnkit.models import CodeExercise, SpotBugExercise

CASES: list[tuple[str, str, str]] = []
for lesson in load_course().lessons():
    for ex in lesson.exercises:
        if isinstance(ex, CodeExercise) and ex.spark_tests:
            CASES.append((ex.id, ex.solution, ex.spark_tests))
        if isinstance(ex, SpotBugExercise) and ex.spark_tests:
            CASES.append((ex.id, ex.fix_solution, ex.spark_tests))

PRELUDE = """
from delta.tables import DeltaTable
from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql import types as T
"""


@pytest.mark.parametrize(("ex_id", "solution", "tests"), CASES, ids=[c[0] for c in CASES])
def test_solution_runs_on_spark(spark: SparkSession, ex_id: str, solution: str, tests: str) -> None:
    module = types.ModuleType(f"content_{ex_id.replace('-', '_')}")
    sys.modules[module.__name__] = module
    namespace: dict[str, Any] = module.__dict__
    namespace["spark"] = spark
    try:
        exec(PRELUDE, namespace)
        exec(solution, namespace)
        exec(tests, namespace)
    finally:
        sys.modules.pop(module.__name__, None)
