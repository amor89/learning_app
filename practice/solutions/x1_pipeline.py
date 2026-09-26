"""Capstone 1 reference solution: the NAT survey pipeline refactored to the CLAUDE.md standard.

Grain:
- bronze `nat_raw`: one row per delivered record, append-only, with audit columns.
- silver `nat_respondents`: one row per respondent per wave.
- gold `nat_metrics`: one row per tracker x wave x age_group x region.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from delta.tables import DeltaTable
from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql import types as T

Severity = Literal["CRITICAL", "WARN"]
Status = Literal["PASS", "FAIL", "WARN"]

REQUIRED_CONFIG_KEYS = (
    "tracker_id",
    "column_map",
    "type_map",
    "merge_keys",
    "weight_sum_min",
    "weight_sum_max",
    "max_null_weights",
)
ALLOWED_TYPES = frozenset({"string", "int", "bigint", "double", "boolean", "date", "timestamp"})
GOLD_GRAIN = ("tracker_id", "wave_id", "age_group", "region")
ORDER_COLUMN = "delivery_version"

RUN_LOG_SCHEMA = T.StructType(
    [
        T.StructField("run_id", T.StringType(), nullable=False),
        T.StructField("pipeline_name", T.StringType(), nullable=False),
        T.StructField("tracker_id", T.StringType(), nullable=False),
        T.StructField("wave_id", T.StringType(), nullable=False),
        T.StructField("layer", T.StringType(), nullable=False),
        T.StructField("rows_processed", T.LongType(), nullable=False),
        T.StructField("status", T.StringType(), nullable=False),
        T.StructField("error_message", T.StringType(), nullable=True),
        T.StructField("run_timestamp", T.TimestampType(), nullable=False),
    ]
)


# Configuration --------------------------------------------------------------


@dataclass(frozen=True)
class PipelineConfig:
    """Validated pipeline configuration for one tracker."""

    tracker_id: str
    column_map: dict[str, str]
    type_map: dict[str, str]
    merge_keys: tuple[str, ...]
    weight_sum_min: float
    weight_sum_max: float
    max_null_weights: int

    def __post_init__(self) -> None:
        """Fail fast on values that cannot be right.

        Raises:
            ValueError: If a value is empty, out of range or of an unknown type.
        """
        if not self.tracker_id:
            raise ValueError("tracker_id must not be empty")
        if not self.merge_keys:
            raise ValueError("merge_keys must not be empty")
        if self.weight_sum_min > self.weight_sum_max:
            raise ValueError("weight_sum_min exceeds weight_sum_max")
        if self.max_null_weights < 0:
            raise ValueError("max_null_weights must not be negative")
        unknown = sorted(set(self.type_map.values()) - ALLOWED_TYPES)
        if unknown:
            raise ValueError(f"unknown types in type_map: {unknown}")


def load_config(path: Path) -> PipelineConfig:
    """Load and validate a pipeline config from a JSON file.

    Args:
        path: JSON file with every key in REQUIRED_CONFIG_KEYS.

    Returns:
        The validated configuration.

    Raises:
        ValueError: If keys are missing or values are invalid.
    """
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    missing = [key for key in REQUIRED_CONFIG_KEYS if key not in raw]
    if missing:
        raise ValueError(f"config {path.name} is missing keys: {missing}")
    return PipelineConfig(
        tracker_id=str(raw["tracker_id"]),
        column_map=dict(raw["column_map"]),
        type_map=dict(raw["type_map"]),
        merge_keys=tuple(raw["merge_keys"]),
        weight_sum_min=float(raw["weight_sum_min"]),
        weight_sum_max=float(raw["weight_sum_max"]),
        max_null_weights=int(raw["max_null_weights"]),
    )


# Bronze ---------------------------------------------------------------------


def add_audit_columns(
    df: DataFrame, source_file: str, delivery_version: int, ingestion_id: str
) -> DataFrame:
    """Add the bronze audit columns to a delivery.

    Args:
        df: Delivery as received.
        source_file: Path of the delivered file.
        delivery_version: Version of this delivery for the wave.
        ingestion_id: Identifier shared by every row of this ingestion.

    Returns:
        The delivery with ingestion_id, source_file, ingestion_timestamp and delivery_version.
    """
    return (
        df.withColumn("ingestion_id", F.lit(ingestion_id))
        .withColumn("source_file", F.lit(source_file))
        .withColumn("ingestion_timestamp", F.current_timestamp())
        .withColumn("delivery_version", F.lit(delivery_version))
    )


def last_write_rows(spark: SparkSession, table: str) -> int:
    """Rows written by the latest operation on a Delta table, from its history."""
    metrics = DeltaTable.forName(spark, table).history(1).select("operationMetrics").first()
    return int(metrics[0]["numOutputRows"]) if metrics is not None else 0


def ingest_bronze(
    spark: SparkSession,
    df: DataFrame,
    table: str,
    source_file: str,
    delivery_version: int,
) -> int:
    """Append a delivery to bronze. Bronze is append-only.

    Args:
        spark: Active session.
        df: Delivery as received.
        table: Bronze table name.
        source_file: Path of the delivered file.
        delivery_version: Version of this delivery for the wave.

    Returns:
        Rows appended, read from the Delta history instead of a second scan.
    """
    audited = add_audit_columns(df, source_file, delivery_version, str(uuid.uuid4()))
    audited.write.format("delta").mode("append").saveAsTable(table)
    return last_write_rows(spark, table)


# Silver ---------------------------------------------------------------------


def rename_columns(df: DataFrame, column_map: dict[str, str]) -> DataFrame:
    """Rename source columns to canonical names.

    Raises:
        ValueError: If a source column in the map is missing from the delivery.
    """
    missing = sorted(set(column_map) - set(df.columns))
    if missing:
        raise ValueError(f"delivery is missing columns: {missing}")
    for source, target in column_map.items():
        df = df.withColumnRenamed(source, target)
    return df


def cast_columns(df: DataFrame, type_map: dict[str, str]) -> tuple[DataFrame, dict[str, int]]:
    """Cast columns with try_cast and count values that failed to convert.

    Args:
        df: Frame with canonical column names.
        type_map: Canonical column to Spark type name.

    Returns:
        The cast frame, and the number of non-null values per column that became null.
    """
    if not type_map:
        return df, {}
    failures = df.agg(
        *[
            F.sum(
                (F.col(name).isNotNull() & F.col(name).try_cast(kind).isNull()).cast("int")
            ).alias(name)
            for name, kind in type_map.items()
        ]
    ).first()
    counts = {name: int(failures[name] or 0) for name in type_map} if failures else {}
    for name, kind in type_map.items():
        df = df.withColumn(name, F.col(name).try_cast(kind))
    return df, counts


def latest_per_key(df: DataFrame, keys: list[str], order_col: str) -> DataFrame:
    """Keep the row with the highest order_col for each key."""
    window = Window.partitionBy(*keys).orderBy(F.col(order_col).desc())
    return df.withColumn("_rank", F.row_number().over(window)).filter("_rank = 1").drop("_rank")


def transform_silver(
    bronze_df: DataFrame, config: PipelineConfig
) -> tuple[DataFrame, dict[str, int]]:
    """Bronze delivery to silver grain: canonical names, types, one row per key.

    Returns:
        The silver frame and the cast failure counts.
    """
    renamed = rename_columns(bronze_df, config.column_map)
    typed, failures = cast_columns(renamed, config.type_map)
    return latest_per_key(typed, list(config.merge_keys), ORDER_COLUMN), failures


def upsert_silver(spark: SparkSession, df: DataFrame, table: str, keys: list[str]) -> None:
    """Idempotent MERGE of a deduplicated frame into silver on the merge keys."""
    source = latest_per_key(df, keys, ORDER_COLUMN)
    condition = " AND ".join(f"t.{key} = s.{key}" for key in keys)
    (
        DeltaTable.forName(spark, table)
        .alias("t")
        .merge(source.alias("s"), condition)
        .whenMatchedUpdateAll()
        .whenNotMatchedInsertAll()
        .execute()
    )


# Gold -----------------------------------------------------------------------


def compute_gold(silver_df: DataFrame) -> DataFrame:
    """Reach metrics at tracker x wave x age_group x region grain, in-scope rows only."""
    reached = F.col("reach_flag") == 1
    return (
        silver_df.filter(F.col("in_scope"))
        .groupBy(*GOLD_GRAIN)
        .agg(
            F.count("*").alias("unweighted_n"),
            F.sum("final_weight").alias("weighted_base"),
            F.coalesce(F.sum(F.when(reached, F.col("final_weight"))), F.lit(0.0)).alias(
                "weighted_reach"
            ),
            F.coalesce(F.sum(F.when(reached, 1)), F.lit(0)).alias("unweighted_reach"),
        )
        .withColumn("weighted_reach_pct", F.try_divide("weighted_reach", "weighted_base"))
    )


# Quality checks -------------------------------------------------------------


@dataclass(frozen=True)
class CheckResult:
    """One structured QA result."""

    check_name: str
    status: Status
    expected: str
    actual: str
    severity: Severity


class CriticalCheckFailedError(RuntimeError):
    """A CRITICAL check failed and the pipeline must stop."""


def run_checks(
    silver_df: DataFrame, config: PipelineConfig, cast_failures: dict[str, int]
) -> list[CheckResult]:
    """Silver QA checks computed in one aggregation pass.

    Args:
        silver_df: Silver frame for one tracker and wave.
        config: Pipeline configuration with thresholds.
        cast_failures: Output of cast_columns.

    Returns:
        One CheckResult per check.
    """
    keys = list(config.merge_keys)
    row = silver_df.agg(
        F.count("*").alias("rows"),
        F.sum(F.col("final_weight").isNull().cast("int")).alias("null_weights"),
        F.sum("final_weight").alias("weight_sum"),
        F.count_distinct(*[F.col(k) for k in keys]).alias("distinct_keys"),
    ).first()
    rows = int(row["rows"]) if row else 0
    null_weights = int(row["null_weights"] or 0) if row else 0
    weight_sum = float(row["weight_sum"]) if row and row["weight_sum"] is not None else 0.0
    distinct_keys = int(row["distinct_keys"]) if row else 0
    bad_casts = sum(cast_failures.values())

    def result(name: str, ok: bool, expected: str, actual: str, severity: Severity) -> CheckResult:
        failed_status: Status = "FAIL" if severity == "CRITICAL" else "WARN"
        return CheckResult(name, "PASS" if ok else failed_status, expected, actual, severity)

    return [
        result("row_count", rows > 0, "> 0", str(rows), "CRITICAL"),
        result(
            "null_weights",
            null_weights <= config.max_null_weights,
            f"<= {config.max_null_weights}",
            str(null_weights),
            "CRITICAL",
        ),
        result(
            "weight_sum",
            config.weight_sum_min <= weight_sum <= config.weight_sum_max,
            f"{config.weight_sum_min}-{config.weight_sum_max}",
            f"{weight_sum:.1f}",
            "CRITICAL",
        ),
        result("key_uniqueness", distinct_keys == rows, str(rows), str(distinct_keys), "CRITICAL"),
        result("cast_failures", bad_casts == 0, "0", str(bad_casts), "WARN"),
    ]


def enforce(results: list[CheckResult]) -> None:
    """Stop the pipeline on a CRITICAL failure.

    Raises:
        CriticalCheckFailedError: Naming every failed CRITICAL check.
    """
    failed = [r.check_name for r in results if r.severity == "CRITICAL" and r.status == "FAIL"]
    if failed:
        raise CriticalCheckFailedError(f"CRITICAL checks failed: {failed}")


# Run log and incremental loads ---------------------------------------------


def build_run_record(
    pipeline_name: str,
    tracker_id: str,
    wave_id: str,
    layer: str,
    rows_processed: int,
    status: str,
    error_message: str | None = None,
) -> dict[str, Any]:
    """One run log record with a new run id and an aware UTC timestamp."""
    return {
        "run_id": str(uuid.uuid4()),
        "pipeline_name": pipeline_name,
        "tracker_id": tracker_id,
        "wave_id": wave_id,
        "layer": layer,
        "rows_processed": rows_processed,
        "status": status,
        "error_message": error_message,
        "run_timestamp": datetime.now(UTC),
    }


def log_run(spark: SparkSession, record: dict[str, Any], table: str) -> None:
    """Append one record to the run log with an explicit schema."""
    spark.createDataFrame([record], RUN_LOG_SCHEMA).write.format("delta").mode(
        "append"
    ).saveAsTable(table)


def get_unprocessed_waves(
    spark: SparkSession, bronze_table: str, silver_table: str, tracker_id: str
) -> list[str]:
    """Waves in bronze for a tracker that silver does not hold for the same tracker.

    Returns:
        Wave ids sorted by their number.
    """
    same_tracker = F.col("tracker_id") == tracker_id
    bronze = spark.table(bronze_table).filter(same_tracker).select("wave_id").distinct()
    silver = spark.table(silver_table).filter(same_tracker).select("wave_id").distinct()
    waves = [row["wave_id"] for row in bronze.subtract(silver).collect()]
    return sorted(waves, key=lambda wave: int(wave[1:]))
