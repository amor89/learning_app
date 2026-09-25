"""Bronze layer ingestion.

Rules:
- Preserve the exact delivery as received. Never transform, clean or filter.
- Grain: one row per respondent per wave per delivery file.
- Redeliveries append with a new ingestion_id. Never replace.
"""
import uuid

from pyspark.sql import SparkSession
from pyspark.sql.functions import current_timestamp, lit

spark = SparkSession.builder.getOrCreate()


def ingest_to_bronze(
    source_path: str,
    tracker_id: str,
    wave_id: str,
    delivery_version: int,
    target_table: str,
) -> int:
    """
    Ingest a delivery file to the bronze layer.
    Appends to the Delta table. Never overwrites.
    Returns row count ingested.
    """
    df = spark.read.option("header", True).csv(source_path)

    ingestion_id = str(uuid.uuid4())

    df_augmented = (
        df
        .withColumn("ingestion_id",        lit(ingestion_id))
        .withColumn("tracker_id",          lit(tracker_id))
        .withColumn("wave_id",             lit(wave_id))
        .withColumn("source_file",         lit(source_path))
        .withColumn("ingestion_timestamp", current_timestamp())
        .withColumn("delivery_version",    lit(delivery_version))
    )

    row_count = df_augmented.count()

    df_augmented.write.format("delta").mode("append").saveAsTable(target_table)

    return row_count
