"""Silver layer: rename to canonical names, enforce types, MERGE on redelivery.

Rules:
- Grain: one row per respondent per wave.
- Column maps come from the Variable Registry at runtime. Never hardcode them.
- Redeliveries update silver through MERGE. Bronze stays append-only.
"""
from delta.tables import DeltaTable
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, lit

spark = SparkSession.builder.getOrCreate()


def load_column_map(tracker_id: str, wave_id: str) -> dict:
    """Load canonical column mapping from Variable Registry."""
    registry = spark.table("research_governance.variable_registry")
    return {
        row["source_column"]: row["variable_name"]
        for row in registry.filter(
            (registry.tracker_id == tracker_id) &
            (registry.is_active == True)
        ).collect()
    }


def transform_to_silver(
    bronze_df: DataFrame,
    column_map: dict,
    type_map: dict,
    wave_id: str,
) -> DataFrame:
    """
    Transform bronze delivery to silver schema.
    column_map: {source_col: canonical_col}
    type_map: {canonical_col: spark_type}
    """
    for src, tgt in column_map.items():
        bronze_df = bronze_df.withColumnRenamed(src, tgt)

    for col_name, col_type in type_map.items():
        bronze_df = bronze_df.withColumn(col_name, col(col_name).cast(col_type))

    bronze_df = bronze_df.withColumn("wave_id", lit(wave_id))

    return bronze_df


def upsert_silver(
    new_df: DataFrame,
    target_table: str,
    merge_keys: list,
) -> None:
    """
    Merge new data into silver table.
    Matches on merge_keys (e.g. respondent_id + wave_id).
    Updates changed rows; inserts new rows.
    """
    delta_table = DeltaTable.forName(spark, target_table)
    merge_condition = " AND ".join(
        [f"target.{k} = source.{k}" for k in merge_keys]
    )

    (
        delta_table.alias("target")
        .merge(new_df.alias("source"), merge_condition)
        .whenMatchedUpdateAll()
        .whenNotMatchedInsertAll()
        .execute()
    )
