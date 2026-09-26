# Capstone 1 starting point: a notebook exported as one script. Do not fix this file.
# Refactor it into practice/exercises/x1_pipeline.py. Every defect below is deliberate.
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, lit, sum, when
from delta.tables import DeltaTable

spark = SparkSession.builder.getOrCreate()

COLUMN_MAP = {"RESP_ID": "respondent_id", "WAVE": "wave_id", "AGE_GRP": "age_group",
              "REGION": "region", "INSCOPE": "in_scope", "REACH": "reach_flag", "WGT": "final_weight"}
TOKEN = "paste-token-here"


def run(path, wave_id, checks=[]):
    df = spark.read.option("header", True).csv(path)
    n = df.count()
    df.write.mode("overwrite").saveAsTable("nat_raw")

    for src, tgt in COLUMN_MAP.items():
        df = df.withColumnRenamed(src, tgt)
    df = df.withColumn("final_weight", col("final_weight").cast("double"))
    df = df.withColumn("reach_flag", col("reach_flag").cast("int"))

    DeltaTable.forName(spark, "nat_respondents").alias("t").merge(
        df.alias("s"), "t.respondent_id = s.respondent_id AND t.wave_id = s.wave_id"
    ).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()

    gold = (df.filter(col("in_scope") == True)
            .groupBy("wave_id", "age_group", "region")
            .agg(count("*").alias("unweighted_n"),
                 sum("final_weight").alias("weighted_base"),
                 sum(when(col("reach_flag") == 1, col("final_weight"))).alias("weighted_reach"),
                 sum(when(col("reach_flag") == 1, 1)).alias("unweighted_reach"))
            .withColumn("weighted_reach_pct", col("weighted_reach") / col("weighted_base")))
    gold.write.mode("overwrite").saveAsTable("nat_metrics")

    if df.filter(col("final_weight").isNull()).count() > 0:
        checks.append("null weights found")
    if df.count() != df.select("respondent_id").distinct().count():
        checks.append("duplicate respondents")
    passed = sum(1 for c in checks if c.startswith("ok"))

    spark.createDataFrame([{"run_id": str(uuid.uuid4()), "wave_id": wave_id, "rows": n,
                            "status": "done", "error_message": None,
                            "ts": datetime.utcnow().isoformat()}]).write.mode("append").saveAsTable("run_log")
    return checks
