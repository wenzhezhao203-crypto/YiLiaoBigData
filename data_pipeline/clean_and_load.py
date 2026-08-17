"""Clean hospital discharge CSV/TSV data with Pandas and load it into MySQL."""

from __future__ import annotations

import argparse
import hashlib
import os
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.mysql import insert as mysql_insert


TABLE_NAME = "inpatient_discharges"
DEFAULT_CHUNK_SIZE = 50_000
DEFAULT_SOURCE_PATH = Path(
    r"C:\Users\86180\Desktop\大数据医疗项目\Hospital_Inpatient_Discharges__SPARCS_De-Identified___2021_20231012.csv\Hospital_Inpatient_Discharges__SPARCS_De-Identified___2021_20231012.csv"
)

# Some source extracts name this field County instead of Hospital County.
COLUMN_MAP = {
    "Hospital Service Area": "hospital_service_area",
    "Hospital County": "hospital_county",
    "County": "hospital_county",
    "Operating Certificate Number": "operating_certificate_number",
    "Permanent Facility Id": "permanent_facility_id",
    "Facility Name": "facility_name",
    "Age Group": "age_group",
    "Zip Code - 3 digits": "zip_code_3",
    "Gender": "gender",
    "Race": "race",
    "Ethnicity": "ethnicity",
    "Length of Stay": "length_of_stay",
    "Type of Admission": "type_of_admission",
    "Patient Disposition": "patient_disposition",
    "Discharge Year": "discharge_year",
    "CCSR Diagnosis Code": "ccsr_diagnosis_code",
    "CCSR Diagnosis Description": "ccsr_diagnosis_description",
    "CCSR Procedure Code": "ccsr_procedure_code",
    "CCSR Procedure Description": "ccsr_procedure_description",
    "APR DRG Code": "apr_drg_code",
    "APR DRG Description": "apr_drg_description",
    "APR MDC Code": "apr_mdc_code",
    "APR MDC Description": "apr_mdc_description",
    "APR Severity of Illness Code": "apr_severity_code",
    "APR Severity of Illness Description": "apr_severity_description",
    "APR Risk of Mortality": "apr_risk_of_mortality",
    "APR Medical Surgical Description": "apr_medical_surgical_description",
    "Payment Typology 1": "payment_typology_1",
    "Payment Typology 2": "payment_typology_2",
    "Payment Typology 3": "payment_typology_3",
    "Birth Weight": "birth_weight",
    "Emergency Department Indicator": "emergency_department_indicator",
    "Total Charges": "total_charges",
    "Total Costs": "total_costs",
}

RAW_COLUMNS = list(dict.fromkeys(COLUMN_MAP.values()))
REQUIRED_SOURCE_COLUMNS = {"discharge_year", "ccsr_diagnosis_code", "length_of_stay"}
REQUIRED_VALUE_COLUMNS = ["facility_name", "discharge_year", "ccsr_diagnosis_code", "length_of_stay"]
NUMERIC_COLUMNS = [
    "length_of_stay",
    "discharge_year",
    "apr_severity_code",
    "apr_risk_of_mortality",
    "birth_weight",
    "total_charges",
    "total_costs",
]
AGE_GROUP_SORT = {
    "0 to 17": 1,
    "18 to 29": 2,
    "30 to 49": 3,
    "50 to 69": 4,
    "70 or Older": 5,
}
OUTPUT_COLUMNS = [
    "source_row_hash",
    "source_file_name",
    "source_row_number",
    "hospital_service_area",
    "hospital_county",
    "operating_certificate_number",
    "permanent_facility_id",
    "facility_name",
    "is_facility_redacted",
    "age_group",
    "age_group_sort",
    "zip_code_3",
    "zip_region_type",
    "gender",
    "race",
    "ethnicity",
    "length_of_stay",
    "type_of_admission",
    "emergency_department_indicator",
    "patient_disposition",
    "disposition_group",
    "discharge_year",
    "ccsr_diagnosis_code",
    "ccsr_diagnosis_description",
    "ccsr_procedure_code",
    "ccsr_procedure_description",
    "apr_drg_code",
    "apr_drg_description",
    "apr_mdc_code",
    "apr_mdc_description",
    "apr_severity_code",
    "apr_severity_description",
    "apr_risk_of_mortality",
    "apr_medical_surgical_description",
    "payment_typology_1",
    "payment_typology_2",
    "payment_typology_3",
    "birth_weight",
    "total_charges",
    "total_costs",
    "charge_cost_gap",
]


def normalize_text(series: pd.Series) -> pd.Series:
    """Trim text but keep code fields as strings so leading zeros are retained."""
    return series.astype("string").str.strip().replace({"": pd.NA})


def normalize_number(series: pd.Series) -> pd.Series:
    """Convert values such as '1,027,545.65' and '$300.00' to numeric values."""
    text_value = normalize_text(series).str.replace(",", "", regex=False).str.replace("$", "", regex=False)
    return pd.to_numeric(text_value, errors="coerce")


def canonicalize(series: pd.Series, aliases: dict[str, str]) -> pd.Series:
    """Apply aliases while preserving unrecognised source values for later review."""
    original = normalize_text(series)
    return original.str.upper().map(aliases).fillna(original)


def row_hash(frame: pd.DataFrame) -> pd.Series:
    """Hash normalized source fields only; metadata must not affect duplicate detection."""
    payload = frame[RAW_COLUMNS].astype("string").fillna("<NULL>").agg("|".join, axis=1)
    return payload.map(lambda item: hashlib.sha256(item.encode("utf-8")).hexdigest())


def empty_summary() -> dict[str, int]:
    return {
        "input_rows": 0,
        "clean_rows": 0,
        "inserted_rows": 0,
        "exact_duplicate_rows": 0,
        "discarded_core_missing_rows": 0,
        "discarded_redacted_facility_rows": 0,
        "invalid_numeric_values": 0,
        "code_description_mismatches": 0,
    }


def clean_chunk(raw: pd.DataFrame, source_name: str) -> tuple[pd.DataFrame, dict[str, int]]:
    """Apply documented cleaning rules to one Pandas chunk without statistical outlier logic."""
    summary = empty_summary()
    summary["input_rows"] = len(raw)
    source_row_number = raw.index.to_series().add(2).to_numpy()
    frame = raw.rename(columns=COLUMN_MAP).copy()
    frame = frame.loc[:, ~frame.columns.duplicated()]

    missing_headers = REQUIRED_SOURCE_COLUMNS - set(frame.columns)
    if missing_headers:
        missing = ", ".join(sorted(missing_headers))
        raise ValueError(f"Source file is missing required columns: {missing}")

    # Include absent optional fields as NULL so all file variants produce one schema.
    frame = frame.reindex(columns=RAW_COLUMNS)
    for column in RAW_COLUMNS:
        frame[column] = normalize_text(frame[column])

    for column in NUMERIC_COLUMNS:
        before = frame[column].notna().sum()
        frame[column] = normalize_number(frame[column])
        summary["invalid_numeric_values"] += int(before - frame[column].notna().sum())

    invalid_los = frame["length_of_stay"].lt(0).fillna(False)
    invalid_year = frame["discharge_year"].notna() & ~frame["discharge_year"].between(2000, date.today().year)
    invalid_severity = ~frame["apr_severity_code"].isin([1, 2, 3, 4]) & frame["apr_severity_code"].notna()
    invalid_risk = ~frame["apr_risk_of_mortality"].isin([1, 2, 3, 4]) & frame["apr_risk_of_mortality"].notna()
    invalid_money_or_weight = pd.DataFrame(
        {
            "total_charges": frame["total_charges"].lt(0).fillna(False),
            "total_costs": frame["total_costs"].lt(0).fillna(False),
            "birth_weight": frame["birth_weight"].le(0).fillna(False),
        }
    )
    summary["invalid_numeric_values"] += int(
        invalid_los.sum() + invalid_year.sum() + invalid_severity.sum() + invalid_risk.sum() + invalid_money_or_weight.sum().sum()
    )
    frame.loc[invalid_los, "length_of_stay"] = pd.NA
    frame.loc[invalid_year, "discharge_year"] = pd.NA
    frame.loc[invalid_severity, "apr_severity_code"] = pd.NA
    frame.loc[invalid_risk, "apr_risk_of_mortality"] = pd.NA
    for column in invalid_money_or_weight.columns:
        frame.loc[invalid_money_or_weight[column], column] = pd.NA

    frame["gender"] = canonicalize(frame["gender"], {"M": "M", "MALE": "M", "F": "F", "FEMALE": "F"})
    frame["type_of_admission"] = canonicalize(
        frame["type_of_admission"],
        {"EMERGENCY": "Emergency", "URGENT": "Urgent", "ELECTIVE": "Elective", "NEWBORN": "Newborn"},
    )
    frame["apr_medical_surgical_description"] = canonicalize(
        frame["apr_medical_surgical_description"], {"MEDICAL": "Medical", "SURGICAL": "Surgical"}
    )
    frame["emergency_department_indicator"] = canonicalize(
        frame["emergency_department_indicator"],
        {"Y": "Y", "YES": "Y", "TRUE": "Y", "1": "Y", "N": "N", "NO": "N", "FALSE": "N", "0": "N"},
    )
    valid_emergency = frame["emergency_department_indicator"].isin(["Y", "N"])
    frame.loc[~valid_emergency & frame["emergency_department_indicator"].notna(), "emergency_department_indicator"] = pd.NA

    frame["age_group_sort"] = frame["age_group"].map(AGE_GROUP_SORT).astype("Int64")
    zip_text = normalize_text(frame["zip_code_3"]).str.upper()
    frame["zip_code_3"] = zip_text
    frame["zip_region_type"] = pd.Series(pd.NA, index=frame.index, dtype="string")
    frame.loc[zip_text.eq("OOS"), "zip_region_type"] = "OUT_OF_STATE"
    frame.loc[zip_text.str.fullmatch(r"\d{3}", na=False), "zip_region_type"] = "LOCAL"
    frame.loc[zip_text.notna() & frame["zip_region_type"].isna(), "zip_region_type"] = "UNKNOWN"

    is_redacted = frame["facility_name"].str.upper().eq("REDACTED FOR CONFIDENTIALITY").fillna(False)
    frame["is_facility_redacted"] = is_redacted.astype("Int64")
    frame["disposition_group"] = pd.Series(pd.NA, index=frame.index, dtype="string")

    # Records without identifiable hospital information are outside hospital-level analysis.
    summary["discarded_redacted_facility_rows"] = int(is_redacted.sum())
    frame = frame.loc[~is_redacted].copy()
    source_row_number = source_row_number[~is_redacted.to_numpy()]

    non_newborn = frame["type_of_admission"].ne("Newborn").fillna(True)
    frame.loc[non_newborn, "birth_weight"] = pd.NA

    mismatch_pairs = [
        ("ccsr_diagnosis_code", "ccsr_diagnosis_description"),
        ("ccsr_procedure_code", "ccsr_procedure_description"),
        ("apr_drg_code", "apr_drg_description"),
        ("apr_mdc_code", "apr_mdc_description"),
    ]
    for left, right in mismatch_pairs:
        summary["code_description_mismatches"] += int((frame[left].isna() ^ frame[right].isna()).sum())

    duplicate_rows = frame.duplicated(subset=RAW_COLUMNS, keep="first")
    summary["exact_duplicate_rows"] = int(duplicate_rows.sum())
    frame = frame.loc[~duplicate_rows].copy()
    source_row_number = source_row_number[~duplicate_rows.to_numpy()]

    missing_core = frame[REQUIRED_VALUE_COLUMNS].isna().any(axis=1)
    summary["discarded_core_missing_rows"] = int(missing_core.sum())
    frame = frame.loc[~missing_core].copy()
    source_row_number = source_row_number[~missing_core.to_numpy()]

    frame["source_row_hash"] = row_hash(frame)
    frame["source_file_name"] = source_name
    frame["source_row_number"] = source_row_number
    frame["charge_cost_gap"] = (frame["total_charges"] - frame["total_costs"]).round(2)
    summary["clean_rows"] = len(frame)
    return frame[OUTPUT_COLUMNS], summary


def insert_ignore(table: Any, connection: Any, keys: list[str], data_iter: Any) -> int:
    """Ignore source_row_hash collisions so imports are safe to rerun."""
    records = [dict(zip(keys, row)) for row in data_iter]
    if not records:
        return 0
    result = connection.execute(mysql_insert(table.table).prefix_with("IGNORE"), records)
    return result.rowcount


def make_engine() -> Any:
    load_dotenv()
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = os.getenv("MYSQL_PORT", "3306")
    database = os.getenv("MYSQL_DATABASE", "medical_platform")
    user = os.getenv("MYSQL_USER", "medical_app")
    password = os.getenv("MYSQL_PASSWORD", "123456")
    return create_engine(
        f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4",
        pool_pre_ping=True,
    )


def load_file(source: Path, chunksize: int) -> dict[str, int]:
    """Read a source file in chunks, clean it, and batch insert the main table only."""
    delimiter = "\t" if source.suffix.lower() == ".tsv" else ","
    engine = make_engine()
    summary = empty_summary()

    with engine.connect() as connection:
        connection.execute(text(f"SELECT 1 FROM {TABLE_NAME} LIMIT 1"))

    reader = pd.read_csv(
        source,
        sep=delimiter,
        dtype="string",
        chunksize=chunksize,
        encoding="utf-8-sig",
        na_values=["", " ", "N/A", "NA", "NULL", "null"],
        keep_default_na=True,
        on_bad_lines="warn",
    )
    for raw_chunk in reader:
        clean, chunk_summary = clean_chunk(raw_chunk, source.name)
        for key in summary:
            summary[key] += chunk_summary[key]
        if clean.empty:
            continue
        with engine.begin() as connection:
            inserted = clean.to_sql(
                TABLE_NAME,
                connection,
                if_exists="append",
                index=False,
                method=insert_ignore,
                chunksize=2_000,
            )
        summary["inserted_rows"] += int(inserted or 0)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean hospital discharge data and load it into MySQL.")
    parser.add_argument(
        "source",
        nargs="?",
        type=Path,
        default=DEFAULT_SOURCE_PATH,
        help="Path to a CSV or TSV source file; defaults to the configured 2021 SPARCS CSV.",
    )
    parser.add_argument("--chunksize", type=int, default=DEFAULT_CHUNK_SIZE, help="Rows processed in each Pandas chunk")
    args = parser.parse_args()
    if not args.source.is_file():
        raise FileNotFoundError(f"Source file not found: {args.source}")
    print(load_file(args.source, args.chunksize))


if __name__ == "__main__":
    main()
