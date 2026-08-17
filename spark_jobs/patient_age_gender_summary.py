"""Build the patient age and gender summary used by the BI dashboard."""

from __future__ import annotations

import os

from pyspark.sql import SparkSession, functions as F


MYSQL_HOST = os.getenv("MYSQL_HOST", "mysql")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "medical_platform")
MYSQL_USER = os.getenv("MYSQL_USER", "medical_app")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "123456")
SOURCE_TABLE = "inpatient_discharges"
TARGET_TABLE = "patient_age_gender_summary"
JDBC_URL = f"jdbc:mysql://{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?useUnicode=true&characterEncoding=utf8&serverTimezone=Asia/Shanghai"


def jdbc_options(table_name: str) -> dict[str, str]:
    return {
        "url": JDBC_URL,
        "dbtable": table_name,
        "user": MYSQL_USER,
        "password": MYSQL_PASSWORD,
        "driver": "com.mysql.cj.jdbc.Driver",
    }


def main() -> None:
    spark = (
        SparkSession.builder.appName("MedicalPatientAgeGenderSummary")
        .master("local[*]")
        .config("spark.sql.session.timeZone", "Asia/Shanghai")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    source = spark.read.format("jdbc").options(**jdbc_options(SOURCE_TABLE)).load()
    summary = (
        source.groupBy(
            "hospital_service_area",
            "hospital_county",
            "facility_name",
            "age_group",
            "age_group_sort",
            "gender",
        )
        .agg(F.count("id").alias("discharge_count"))
        .withColumn("updated_at", F.current_timestamp())
    )

    summary.write.format("jdbc").options(**jdbc_options(TARGET_TABLE)).mode("overwrite").save()
    print(f"Completed: {TARGET_TABLE}, rows={summary.count()}")
    spark.stop()


if __name__ == "__main__":
    main()
