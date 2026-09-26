"""Capstone 1: refactor practice/capstone/before_pipeline.py to the CLAUDE.md standard.

Replace each NotImplementedError with your code. Keep the names and signatures:
the acceptance tests import them.

Check your work with: pytest practice/tests/test_x1_pipeline.py
Compare with the reference only after your tests pass: practice/solutions/x1_pipeline.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pyspark.sql import DataFrame, SparkSession

Severity = Literal["CRITICAL", "WARN"]
Status = Literal["PASS", "FAIL", "WARN"]


@dataclass(frozen=True)
class PipelineConfig:
    """Validated pipeline configuration for one tracker. Add a __post_init__ that fails fast."""

    tracker_id: str
    column_map: dict[str, str]
    type_map: dict[str, str]
    merge_keys: tuple[str, ...]
    weight_sum_min: float
    weight_sum_max: float
    max_null_weights: int


def load_config(path: Path) -> PipelineConfig:
    """Load and validate practice/capstone/nat_config.json. Raise ValueError naming missing keys."""
    raise NotImplementedError


def ingest_bronze(
    spark: SparkSession, df: DataFrame, table: str, source_file: str, delivery_version: int
) -> int:
    """Append a delivery with the four audit columns. Return rows appended without a second scan."""
    raise NotImplementedError


def transform_silver(
    bronze_df: DataFrame, config: PipelineConfig
) -> tuple[DataFrame, dict[str, int]]:
    """Rename (raise if a column is missing), try_cast with failure counts, latest row per key."""
    raise NotImplementedError


def upsert_silver(spark: SparkSession, df: DataFrame, table: str, keys: list[str]) -> None:
    """Idempotent MERGE on the keys, deduplicating the source first."""
    raise NotImplementedError


def compute_gold(silver_df: DataFrame) -> DataFrame:
    """In-scope reach metrics at tracker x wave x age_group x region grain. Zero, not null."""
    raise NotImplementedError


@dataclass(frozen=True)
class CheckResult:
    """One structured QA result."""

    check_name: str
    status: Status
    expected: str
    actual: str
    severity: Severity


def run_checks(
    silver_df: DataFrame, config: PipelineConfig, cast_failures: dict[str, int]
) -> list[CheckResult]:
    """row_count, null_weights, weight_sum, key_uniqueness (CRITICAL) and cast_failures (WARN)."""
    raise NotImplementedError


def enforce(results: list[CheckResult]) -> None:
    """Raise a RuntimeError subclass naming every failed CRITICAL check."""
    raise NotImplementedError


def build_run_record(
    pipeline_name: str,
    tracker_id: str,
    wave_id: str,
    layer: str,
    rows_processed: int,
    status: str,
    error_message: str | None = None,
) -> dict[str, Any]:
    """One run log record with a new run_id and an aware UTC run_timestamp."""
    raise NotImplementedError


def log_run(spark: SparkSession, record: dict[str, Any], table: str) -> None:
    """Append the record to the run log table with an explicit StructType schema."""
    raise NotImplementedError


def get_unprocessed_waves(
    spark: SparkSession, bronze_table: str, silver_table: str, tracker_id: str
) -> list[str]:
    """Tracker waves in bronze but not silver, filtered on both sides, sorted by number."""
    raise NotImplementedError
