"""Run logging, Delta table health checks and incremental processing."""
from pyspark.sql import SparkSession
from pyspark.sql.functions import col

spark = SparkSession.builder.getOrCreate()


def log_pipeline_run(
    pipeline_name: str,
    tracker_id: str,
    wave_id: str,
    layer: str,
    rows_processed: int,
    status: str,
    error_message: str = None,
) -> None:
    """Append one record per pipeline run to the governance run log."""
    run_record = spark.createDataFrame([{
        "run_id":         str(uuid.uuid4()),
        "pipeline_name":  pipeline_name,
        "tracker_id":     tracker_id,
        "wave_id":        wave_id,
        "layer":          layer,
        "rows_processed": rows_processed,
        "status":         status,
        "error_message":  error_message,
        "run_timestamp":  datetime.utcnow().isoformat(),
    }])

    run_record.write.format("delta").mode("append").saveAsTable(
        "research_governance.pipeline_run_log"
    )


def check_table_health(table_name: str) -> dict:
    """Run after every wave load to confirm table health."""
    df = spark.table(table_name)
    return {
        "table":          table_name,
        "row_count":      df.count(),
        "null_ids":       df.filter(col("respondent_id").isNull()).count(),
        "null_weights":   df.filter(col("final_weight").isNull()).count(),
        "min_weight":     df.agg({"final_weight": "min"}).collect()[0][0],
        "max_weight":     df.agg({"final_weight": "max"}).collect()[0][0],
        "distinct_waves": df.select("wave_id").distinct().count(),
    }


def get_unprocessed_waves(
    bronze_table: str,
    silver_table: str,
    tracker_id: str,
) -> list:
    """Return wave IDs present in bronze but not yet in silver."""
    bronze_waves = (
        spark.table(bronze_table)
        .filter(col("tracker_id") == tracker_id)
        .select("wave_id")
        .distinct()
    )
    silver_waves = (
        spark.table(silver_table)
        .select("wave_id")
        .distinct()
    )
    return [
        row.wave_id for row in
        bronze_waves.subtract(silver_waves).collect()
    ]
