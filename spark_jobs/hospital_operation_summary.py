"""Build the hospital operation summary used by the BI dashboard center panel."""

from __future__ import annotations

import os

from pyspark.sql import SparkSession, functions as F


MYSQL_HOST = os.getenv("MYSQL_HOST", "mysql")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "medical_platform")
MYSQL_USER = os.getenv("MYSQL_USER", "medical_app")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "123456")
SOURCE_TABLE = "inpatient_discharges"
TARGET_TABLE = "hospital_operation_summary"
FILTER_COLUMNS = ["hospital_service_area", "hospital_county", "facility_name"]
JDBC_URL = f"jdbc:mysql://{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?useUnicode=true&characterEncoding=utf8&serverTimezone=Asia/Shanghai"


def jdbc_options(table_name: str) -> dict[str, str]:
    return {
        "url": JDBC_URL,
        "dbtable": table_name,
        "user": MYSQL_USER,
        "password": MYSQL_PASSWORD,
        "driver": "com.mysql.cj.jdbc.Driver",
        "fetchsize": "10000",
    }


def main() -> None:
    spark = (
        SparkSession.builder.appName("MedicalHospitalOperationSummary")
        .master("local[*]")
        .config("spark.sql.session.timeZone", "Asia/Shanghai")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    source = spark.read.format("jdbc").options(**jdbc_options(SOURCE_TABLE)).load()
    summary = (
        source.groupBy(*FILTER_COLUMNS)
        .agg(
            F.count("id").alias("discharge_count"),
            F.sum("length_of_stay").alias("length_of_stay_sum"),
            F.sum("total_charges").alias("total_charges_sum"),
            F.sum("total_costs").alias("total_costs_sum"),
            F.sum("charge_cost_gap").alias("charge_cost_gap_sum"),
            F.sum(
                F.when(F.col("emergency_department_indicator") == "Y", F.col("total_charges")).otherwise(0)
            ).alias("emergency_charges_sum"),
            F.sum(
                F.when(F.col("emergency_department_indicator") == "N", F.col("total_charges")).otherwise(0)
            ).alias("non_emergency_charges_sum"),
            F.sum(
                F.when(F.col("emergency_department_indicator") == "Y", F.col("total_costs")).otherwise(0)
            ).alias("emergency_costs_sum"),
            F.sum(
                F.when(F.col("emergency_department_indicator") == "N", F.col("total_costs")).otherwise(0)
            ).alias("non_emergency_costs_sum"),
            F.sum(
                F.when(F.col("emergency_department_indicator") == "Y", 1).otherwise(0)
            ).alias("emergency_yes_count"),
            F.sum(
                F.when(
                    F.col("emergency_department_indicator").isin("Y", "N"), 1
                ).otherwise(0)
            ).alias("emergency_known_count"),
        )
        .withColumn("updated_at", F.current_timestamp())
    )

    summary.write.format("jdbc").options(**jdbc_options(TARGET_TABLE)).mode("overwrite").save()
    print(f"Completed: {TARGET_TABLE}")
    spark.stop()


if __name__ == "__main__":
    main()
