"""A3-L1 reference solution: idempotent MERGE with a deduplicated source."""

from __future__ import annotations

from delta.tables import DeltaTable
from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F


def latest_per_key(df: DataFrame, keys: list[str], order_col: str) -> DataFrame:
    """Keep the row with the highest order_col for each key.

    Args:
        df: Source rows, possibly with repeated keys.
        keys: Columns that identify one target row.
        order_col: Column that ranks versions. Highest wins.

    Returns:
        One row per key.
    """
    window = Window.partitionBy(*keys).orderBy(F.col(order_col).desc())
    return (
        df.withColumn("_rank", F.row_number().over(window))
        .filter(F.col("_rank") == 1)
        .drop("_rank")
    )


def upsert_silver(
    spark: SparkSession,
    source: DataFrame,
    target_table: str,
    keys: list[str],
    order_col: str,
) -> None:
    """MERGE the newest source row per key into a Delta table.

    Running it twice with the same source leaves the table unchanged.
    """
    condition = " AND ".join(f"t.{k} = s.{k}" for k in keys)
    (
        DeltaTable.forName(spark, target_table)
        .alias("t")
        .merge(latest_per_key(source, keys, order_col).alias("s"), condition)
        .whenMatchedUpdateAll()
        .whenNotMatchedInsertAll()
        .execute()
    )
