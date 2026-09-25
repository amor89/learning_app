"""Shared fixtures for laptop practice: a local SparkSession with Delta Lake.

Run your own answers:      pytest practice
Run the reference answers: pytest practice --solutions
Needs Java 17 or 21 and the `spark` dependency group (pyspark 4.0.4, delta-spark 4.0.1).
"""

from __future__ import annotations

import importlib
import os
import shutil
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest
from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--solutions",
        action="store_true",
        help="Test practice/solutions instead of practice/exercises.",
    )


@pytest.fixture(scope="session")
def spark() -> Iterator[SparkSession]:
    """One local Spark session with Delta, shared by every test."""
    # Workers must use this interpreter, or pandas UDFs cannot import pandas.
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    warehouse = Path(tempfile.mkdtemp(prefix="practice-warehouse-"))
    builder = (
        SparkSession.builder.master("local[2]")
        .appName("practice")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog"
        )
        .config("spark.sql.warehouse.dir", str(warehouse))
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
        # Databricks defaults saveAsTable to Delta; open-source Spark defaults to Parquet.
        .config("spark.sql.sources.default", "delta")
    )
    session = configure_spark_with_delta_pip(builder).getOrCreate()
    yield session
    session.stop()
    shutil.rmtree(warehouse, ignore_errors=True)


@pytest.fixture(scope="session")
def package(request: pytest.FixtureRequest) -> str:
    """Name of the package under test."""
    return "solutions" if request.config.getoption("--solutions") else "exercises"


def load(package: str, name: str) -> ModuleType:
    """Import practice.<package>.<name>."""
    return importlib.import_module(f"practice.{package}.{name}")
