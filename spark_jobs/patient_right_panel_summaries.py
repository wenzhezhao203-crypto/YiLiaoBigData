"""Build disease and risk summaries used by the BI dashboard right panel."""

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


def base_metrics() -> list:
    """Metrics shared by disease and risk aggregates."""
    return [
        F.count("id").alias("discharge_count"),
        F.sum("length_of_stay").alias("length_of_stay_sum"),
        F.sum("total_charges").alias("total_charges_sum"),
        F.sum("total_costs").alias("total_costs_sum"),
    ]


def write_summary(frame, table_name: str) -> None:
    frame.withColumn("updated_at", F.current_timestamp()).write.format("jdbc").options(
        **jdbc_options(table_name)
    ).mode("overwrite").save()
    print(f"Completed: {table_name}")


def main() -> None:
    spark = (
        SparkSession.builder.appName("MedicalPatientRightPanelSummaries")
        .master("local[*]")
        .config("spark.sql.session.timeZone", "Asia/Shanghai")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    source = spark.read.format("jdbc").options(**jdbc_options(SOURCE_TABLE)).load()

    disease_system_summary = source.groupBy(*FILTER_COLUMNS, "apr_mdc_code").agg(
        F.first("apr_mdc_description", ignorenulls=True).alias("apr_mdc_description"),
        *base_metrics(),
    )
    write_summary(disease_system_summary, "disease_system_summary")

    diagnosis_summary = source.groupBy(*FILTER_COLUMNS, "ccsr_diagnosis_code").agg(
        F.first("ccsr_diagnosis_description", ignorenulls=True).alias(
            "ccsr_diagnosis_description"
        ),
        *base_metrics(),
    )
    write_summary(diagnosis_summary, "diagnosis_summary")

    patient_risk_summary = source.groupBy(
        *FILTER_COLUMNS,
        "apr_severity_code",
        "apr_risk_of_mortality",
    ).agg(
        F.first("apr_severity_description", ignorenulls=True).alias(
            "apr_severity_description"
        ),
        *base_metrics(),
    )
    write_summary(patient_risk_summary, "patient_risk_summary")

    disease_drilldown_summary = source.groupBy(
        *FILTER_COLUMNS,
        "apr_mdc_code",
        "apr_drg_code",
        "ccsr_diagnosis_code",
    ).agg(
        F.first("apr_mdc_description", ignorenulls=True).alias("apr_mdc_description"),
        F.first("apr_drg_description", ignorenulls=True).alias("apr_drg_description"),
        F.first("ccsr_diagnosis_description", ignorenulls=True).alias(
            "ccsr_diagnosis_description"
        ),
        *base_metrics(),
    )
    write_summary(disease_drilldown_summary, "disease_drilldown_summary")

    spark.stop()


if __name__ == "__main__":
    main()
