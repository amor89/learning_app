"""Gold layer: pre-computed aggregates for the semantic layer and Power BI.

Rule: document the grain of every gold table in its table comment.
"""
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, count, sum, when

spark = SparkSession.builder.getOrCreate()


def compute_gold_reach_metrics(
    silver_table: str,
    wave_id: str,
    weight_col: str = "final_weight",
) -> DataFrame:
    """
    Compute reach metrics at tracker x wave x subgroup grain.
    Output is the gold metrics table for one wave.
    """
    silver = spark.table(silver_table).filter(col("wave_id") == wave_id)

    metrics = (
        silver
        .filter(col("in_scope") == True)
        .groupBy("wave_id", "age_group", "gender", "region")
        .agg(
            count("*").alias("unweighted_n"),
            sum(weight_col).alias("weighted_base"),
            sum(when(col("reach_flag") == 1, col(weight_col))).alias("weighted_reach"),
            sum(when(col("reach_flag") == 1, 1)).alias("unweighted_reach"),
        )
        .withColumn(
            "weighted_reach_pct",
            col("weighted_reach") / col("weighted_base"),
        )
    )

    return metrics
