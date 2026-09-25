"""Tests for the A3-L1 practice: idempotent MERGE."""

from __future__ import annotations

from collections.abc import Iterator
from types import ModuleType

import pytest
from delta.tables import DeltaMergeBuilder
from pyspark.sql import DataFrame, SparkSession
from pyspark.testing import assertDataFrameEqual

from practice.conftest import load

SCHEMA = "respondent_id STRING, wave_id STRING, final_weight DOUBLE, delivery_version INT"
KEYS = ["respondent_id", "wave_id"]
TABLE = "nat_respondents"


@pytest.fixture
def impl(package: str) -> ModuleType:
    return load(package, "a3_l1_merge")


@pytest.fixture
def table(spark: SparkSession) -> Iterator[str]:
    spark.sql(f"DROP TABLE IF EXISTS {TABLE}")
    spark.sql(f"CREATE TABLE {TABLE} ({SCHEMA}) USING DELTA")
    yield TABLE
    spark.sql(f"DROP TABLE IF EXISTS {TABLE}")


def frame(spark: SparkSession, rows: list[tuple[str, str, float, int]]) -> DataFrame:
    return spark.createDataFrame(rows, SCHEMA)


def test_latest_per_key_keeps_newest(spark: SparkSession, impl: ModuleType) -> None:
    source = frame(spark, [("R1", "W1", 1.0, 1), ("R1", "W1", 2.0, 2), ("R2", "W1", 3.0, 1)])
    expected = frame(spark, [("R1", "W1", 2.0, 2), ("R2", "W1", 3.0, 1)])
    assertDataFrameEqual(impl.latest_per_key(source, KEYS, "delivery_version"), expected)


def test_merge_twice_is_idempotent(spark: SparkSession, impl: ModuleType, table: str) -> None:
    source = frame(spark, [("R1", "W1", 1.2, 1), ("R2", "W1", 0.8, 1), ("R3", "W1", 1.0, 1)])
    impl.upsert_silver(spark, source, table, KEYS, "delivery_version")
    impl.upsert_silver(spark, source, table, KEYS, "delivery_version")
    assert spark.table(table).count() == 3


def test_redelivery_with_repeated_key_updates(
    spark: SparkSession, impl: ModuleType, table: str
) -> None:
    impl.upsert_silver(spark, frame(spark, [("R1", "W1", 1.0, 1)]), table, KEYS, "delivery_version")
    redelivery = frame(spark, [("R1", "W1", 1.5, 2), ("R1", "W1", 1.1, 1)])
    impl.upsert_silver(spark, redelivery, table, KEYS, "delivery_version")
    assertDataFrameEqual(spark.table(table), frame(spark, [("R1", "W1", 1.5, 2)]))


def test_same_respondent_new_wave_is_inserted(
    spark: SparkSession, impl: ModuleType, table: str
) -> None:
    impl.upsert_silver(spark, frame(spark, [("R1", "W1", 1.0, 1)]), table, KEYS, "delivery_version")
    impl.upsert_silver(spark, frame(spark, [("R1", "W2", 2.0, 1)]), table, KEYS, "delivery_version")
    assert spark.table(table).count() == 2


def test_merge_without_dedup_fails_on_repeated_key(spark: SparkSession, table: str) -> None:
    """Documents the lesson's claim: two source rows for one target row fail the MERGE."""
    from delta.tables import DeltaTable

    spark.createDataFrame([("R1", "W1", 1.0, 1)], SCHEMA).write.format("delta").mode(
        "append"
    ).saveAsTable(table)
    repeated = frame(spark, [("R1", "W1", 1.5, 2), ("R1", "W1", 1.4, 2)])
    with pytest.raises(Exception, match=r"(?i)multiple source rows"):
        (
            DeltaTable.forName(spark, table)
            .alias("t")
            .merge(
                repeated.alias("s"), "t.respondent_id = s.respondent_id AND t.wave_id = s.wave_id"
            )
            .whenMatchedUpdateAll()
            .whenNotMatchedInsertAll()
            .execute()
        )


def test_merge_builder_methods_exist() -> None:
    """Documents the lesson's claim about the delta-spark API."""
    for name in [
        "whenMatchedUpdateAll",
        "whenNotMatchedInsertAll",
        "whenNotMatchedBySourceDelete",
        "execute",
    ]:
        assert hasattr(DeltaMergeBuilder, name), name
