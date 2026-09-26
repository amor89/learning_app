"""Acceptance tests for Capstone 1: the refactored NAT pipeline.

Run your version:      pytest practice/tests/test_x1_pipeline.py
Run the reference:     pytest practice/tests/test_x1_pipeline.py --solutions
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from datetime import UTC
from pathlib import Path
from types import ModuleType

import pytest
from pyspark.sql import DataFrame, SparkSession
from pyspark.testing import assertDataFrameEqual

from practice.conftest import load

CONFIG_PATH = Path(__file__).resolve().parents[1] / "capstone" / "nat_config.json"
RAW_SCHEMA = (
    "RESP_ID STRING, WAVE STRING, TRACKER STRING, AGE_GRP STRING, REGION STRING, "
    "INSCOPE STRING, REACH STRING, WGT STRING, delivery_version INT"
)
SILVER_SCHEMA = (
    "respondent_id STRING, wave_id STRING, tracker_id STRING, age_group STRING, region STRING, "
    "in_scope BOOLEAN, reach_flag INT, final_weight DOUBLE, delivery_version INT"
)


@pytest.fixture
def impl(package: str) -> ModuleType:
    return load(package, "x1_pipeline")


@pytest.fixture
def config(impl: ModuleType) -> object:
    return impl.load_config(CONFIG_PATH)


def raw(spark: SparkSession, rows: Sequence[tuple[object, ...]]) -> DataFrame:
    return spark.createDataFrame(rows, RAW_SCHEMA)


def silver(spark: SparkSession, rows: Sequence[tuple[object, ...]]) -> DataFrame:
    return spark.createDataFrame(rows, SILVER_SCHEMA)


@pytest.fixture
def tables(spark: SparkSession) -> Iterator[dict[str, str]]:
    names = {"bronze": "x1_nat_raw", "silver": "x1_nat_respondents", "log": "x1_run_log"}
    for name in names.values():
        spark.sql(f"DROP TABLE IF EXISTS {name}")
    spark.sql(f"CREATE TABLE {names['silver']} ({SILVER_SCHEMA}) USING DELTA")
    yield names
    for name in names.values():
        spark.sql(f"DROP TABLE IF EXISTS {name}")


# Configuration ----------------------------------------------------------------


def test_config_loads(config: object) -> None:
    assert config.tracker_id == "NAT"  # type: ignore[attr-defined]
    assert config.merge_keys == ("respondent_id", "wave_id")  # type: ignore[attr-defined]


def test_config_missing_key_fails_fast(impl: ModuleType, tmp_path: Path) -> None:
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    del data["merge_keys"]
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="merge_keys"):
        impl.load_config(bad)


# Bronze -----------------------------------------------------------------------


def test_bronze_is_append_only_with_audit_columns(
    spark: SparkSession, impl: ModuleType, tables: dict[str, str]
) -> None:
    first = raw(spark, [("R1", "W14", "NAT", "18-34", "N", "true", "1", "1.5", 1)])
    second = raw(spark, [("R2", "W14", "NAT", "35-54", "S", "true", "0", "0.5", 1)])
    assert impl.ingest_bronze(spark, first, tables["bronze"], "d1.csv", 1) == 1
    assert impl.ingest_bronze(spark, second, tables["bronze"], "d2.csv", 1) == 1
    bronze = spark.table(tables["bronze"])
    assert bronze.count() == 2
    audit = {"ingestion_id", "source_file", "ingestion_timestamp", "delivery_version"}
    assert audit <= set(bronze.columns)
    assert {r["source_file"] for r in bronze.select("source_file").collect()} == {
        "d1.csv",
        "d2.csv",
    }


# Silver -----------------------------------------------------------------------


def test_missing_source_column_raises(
    spark: SparkSession, impl: ModuleType, config: object
) -> None:
    df = raw(spark, [("R1", "W14", "NAT", "18-34", "N", "true", "1", "1.5", 1)]).drop("REGION")
    with pytest.raises(ValueError, match="REGION"):
        impl.transform_silver(df, config)


def test_transform_casts_counts_failures_and_dedupes(
    spark: SparkSession, impl: ModuleType, config: object
) -> None:
    df = raw(
        spark,
        [
            ("R1", "W14", "NAT", "18-34", "N", "true", "1", "1.5", 1),
            ("R1", "W14", "NAT", "18-34", "N", "true", "1", "2.0", 2),
            ("R2", "W14", "NAT", "35-54", "S", "true", "n/a", "1.0", 1),
        ],
    )
    out, failures = impl.transform_silver(df, config)
    assert failures == {"in_scope": 0, "reach_flag": 1, "final_weight": 0}
    expected = silver(
        spark,
        [
            ("R1", "W14", "NAT", "18-34", "N", True, 1, 2.0, 2),
            ("R2", "W14", "NAT", "35-54", "S", True, None, 1.0, 1),
        ],
    )
    assertDataFrameEqual(out.select(*expected.columns), expected)


def test_merge_is_idempotent(spark: SparkSession, impl: ModuleType, tables: dict[str, str]) -> None:
    rows = [
        ("R1", "W14", "NAT", "18-34", "N", True, 1, 1.5, 1),
        ("R1", "W14", "NAT", "18-34", "N", True, 1, 2.5, 2),
    ]
    keys = ["respondent_id", "wave_id"]
    impl.upsert_silver(spark, silver(spark, rows), tables["silver"], keys)
    impl.upsert_silver(spark, silver(spark, rows), tables["silver"], keys)
    result = spark.table(tables["silver"])
    assert result.count() == 1
    row = result.first()
    assert row is not None and row["final_weight"] == 2.5


# Gold -------------------------------------------------------------------------


def test_gold_grain_includes_tracker_and_zero_reach(spark: SparkSession, impl: ModuleType) -> None:
    df = silver(
        spark,
        [
            ("R1", "W14", "NAT", "18-34", "N", True, 1, 2.0, 1),
            ("R2", "W14", "NAT", "18-34", "N", True, 0, 2.0, 1),
            ("R3", "W14", "OTH", "18-34", "N", True, 0, 1.0, 1),
            ("R4", "W14", "NAT", "18-34", "N", False, 1, 5.0, 1),
        ],
    )
    gold = {r["tracker_id"]: r for r in impl.compute_gold(df).collect()}
    assert set(gold) == {"NAT", "OTH"}
    assert gold["NAT"]["unweighted_n"] == 2 and gold["NAT"]["weighted_reach_pct"] == 0.5
    assert gold["OTH"]["unweighted_reach"] == 0 and gold["OTH"]["weighted_reach"] == 0.0


# Checks -----------------------------------------------------------------------


def test_checks_are_structured_and_critical_halts(
    spark: SparkSession, impl: ModuleType, config: object
) -> None:
    df = silver(
        spark,
        [
            ("R1", "W14", "NAT", "18-34", "N", True, 1, None, 1),
            ("R1", "W14", "NAT", "18-34", "N", True, 1, 1.0, 1),
        ],
    )
    results = impl.run_checks(df, config, {"reach_flag": 2})
    status = {r.check_name: (r.status, r.severity) for r in results}
    assert status["null_weights"] == ("FAIL", "CRITICAL")
    assert status["key_uniqueness"] == ("FAIL", "CRITICAL")
    assert status["cast_failures"] == ("WARN", "WARN")
    with pytest.raises(RuntimeError, match="null_weights"):
        impl.enforce(results)


def test_checks_pass_on_clean_data(spark: SparkSession, impl: ModuleType, config: object) -> None:
    df = silver(spark, [("R1", "W14", "NAT", "18-34", "N", True, 1, 1.0, 1)])
    results = impl.run_checks(df, config, {"reach_flag": 0})
    assert all(r.status == "PASS" for r in results)
    impl.enforce(results)


# Run log and incremental ------------------------------------------------------


def test_run_log_record(spark: SparkSession, impl: ModuleType, tables: dict[str, str]) -> None:
    record = impl.build_run_record("nat_silver_pipeline", "NAT", "W14", "silver", 10, "SUCCESS")
    assert record["error_message"] is None
    assert record["run_timestamp"].tzinfo is not None
    assert record["run_timestamp"].utcoffset() == UTC.utcoffset(None)
    impl.log_run(spark, record, tables["log"])
    impl.log_run(
        spark,
        impl.build_run_record("p", "NAT", "W14", "silver", 0, "FAILED", "boom"),
        tables["log"],
    )
    log = spark.table(tables["log"])
    assert log.count() == 2
    assert dict(log.dtypes)["run_timestamp"] == "timestamp"


def test_unprocessed_waves_filter_both_sides(
    spark: SparkSession, impl: ModuleType, tables: dict[str, str]
) -> None:
    spark.createDataFrame(
        [("NAT", "W9"), ("NAT", "W10"), ("NAT", "W11")], "tracker_id STRING, wave_id STRING"
    ).write.format("delta").saveAsTable(tables["bronze"])
    silver(spark, [("R9", "W11", "OTH", "18-34", "N", True, 1, 1.0, 1)]).write.format("delta").mode(
        "append"
    ).saveAsTable(tables["silver"])
    waves = impl.get_unprocessed_waves(spark, tables["bronze"], tables["silver"], "NAT")
    assert waves == ["W9", "W10", "W11"]
