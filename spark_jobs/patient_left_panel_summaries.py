"""Build the payment, disposition, and admission summaries for the BI left panel."""

from __future__ import annotations

import os

from pyspark.sql import SparkSession, functions as F


MYSQL_HOST = os.getenv("MYSQL_HOST", "mysql")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "medical_platform")
MYSQL_USER = os.getenv("MYSQL_USER", "medical_app")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "123456")
SOURCE_TABLE = "inpatient_discharges"
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


def write_summary(frame, table_name: str) -> None:
    frame.withColumn("updated_at", F.current_timestamp()).write.format("jdbc").options(
        **jdbc_options(table_name)
    ).mode("overwrite").save()
    print(f"Completed: {table_name}")


def main() -> None:
    spark = (
        SparkSession.builder.appName("MedicalPatientLeftPanelSummaries")
        .master("local[*]")
        .config("spark.sql.session.timeZone", "Asia/Shanghai")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    # Do not cache the 2M-row JDBC source in the single-node Spark JVM.
    source = spark.read.format("jdbc").options(**jdbc_options(SOURCE_TABLE)).load()

    payment_summary = source.groupBy(*FILTER_COLUMNS, "payment_typology_1").agg(
        F.count("id").alias("discharge_count"),
        F.sum("total_charges").alias("total_charges_sum"),
        F.sum("total_costs").alias("total_costs_sum"),
    )
    write_summary(payment_summary, "patient_payment_summary")

    disposition_summary = source.groupBy(*FILTER_COLUMNS, "patient_disposition").agg(
        F.count("id").alias("discharge_count"),
        F.sum("length_of_stay").alias("length_of_stay_sum"),
        F.sum("total_charges").alias("total_charges_sum"),
        F.sum("total_costs").alias("total_costs_sum"),
    )
    write_summary(disposition_summary, "patient_disposition_summary")

    admission_emergency_summary = source.groupBy(
        *FILTER_COLUMNS,
        "type_of_admission",
        "emergency_department_indicator",
    ).agg(
        F.count("id").alias("discharge_count"),
        F.sum("length_of_stay").alias("length_of_stay_sum"),
    )
    write_summary(admission_emergency_summary, "patient_admission_emergency_summary")

    spark.stop()


if __name__ == "__main__":
    main()
