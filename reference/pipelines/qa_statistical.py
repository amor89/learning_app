"""Statistical QA checks run on silver after transformation."""
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, mean, percentile_approx, stddev, sum, when

spark = SparkSession.builder.getOrCreate()


def check_weight_distribution(df: DataFrame, weight_col: str) -> dict:
    stats = df.agg(
        mean(weight_col).alias("mean"),
        stddev(weight_col).alias("stddev"),
        percentile_approx(weight_col, 0.01).alias("p1"),
        percentile_approx(weight_col, 0.99).alias("p99"),
    ).collect()[0]

    cv = stats["stddev"] / stats["mean"] if stats["mean"] else None

    return {
        "mean":       round(stats["mean"], 4),
        "stddev":     round(stats["stddev"], 4),
        "cv":         round(cv, 4) if cv else None,
        "p1":         stats["p1"],
        "p99":        stats["p99"],
        "cv_warning": cv > 1.5 if cv else False,  # CV > 1.5 flags unusual weight spread
    }


def check_wave_stability(
    silver_table: str,
    current_wave: str,
    prior_wave: str,
    metrics: list,
    tolerance: float = 0.10,
) -> list:
    """
    Compare key metric proportions between waves.
    Flag any change larger than tolerance (default 10pp).
    """
    df = spark.table(silver_table).filter(
        col("wave_id").isin([current_wave, prior_wave])
    )

    results = []
    for metric in metrics:
        wave_stats = (
            df
            .groupBy("wave_id")
            .agg(
                (sum(when(col(metric) == 1, col("final_weight"))) /
                 sum("final_weight")).alias("weighted_pct")
            )
            .collect()
        )
        wave_dict = {row["wave_id"]: row["weighted_pct"] for row in wave_stats}
        current_pct = wave_dict.get(current_wave)
        prior_pct = wave_dict.get(prior_wave)
        if current_pct and prior_pct:
            change = abs(current_pct - prior_pct)
            results.append({
                "metric":       metric,
                "current_wave": current_wave,
                "prior_wave":   prior_wave,
                "current_pct":  round(current_pct, 4),
                "prior_pct":    round(prior_pct, 4),
                "change_pp":    round(change, 4),
                "status":       "WARN" if change > tolerance else "PASS",
            })

    return results
