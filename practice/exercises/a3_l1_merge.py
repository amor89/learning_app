"""A3-L1 practice: idempotent MERGE. Replace each NotImplementedError with your code.

Check your work with: pytest practice/tests/test_a3_l1_merge.py
"""

from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession


def latest_per_key(df: DataFrame, keys: list[str], order_col: str) -> DataFrame:
    """Keep the row with the highest order_col for each key."""
    raise NotImplementedError


def upsert_silver(
    spark: SparkSession,
    source: DataFrame,
    target_table: str,
    keys: list[str],
    order_col: str,
) -> None:
    """MERGE the newest source row per key into a Delta table."""
    raise NotImplementedError
