"""Patient analysis endpoints for the BI dashboard left panel."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from flask import Blueprint, jsonify
from sqlalchemy import text

from src.database import engine
from src.routes.filters import FILTER_FIELDS, error_response, read_optional_parameter


patient_bp = Blueprint("patient", __name__, url_prefix="/api/dashboard/patient")


def read_global_filters() -> dict[str, str | None]:
    """Read the three supported dashboard filters from the query string."""
    return {field: read_optional_parameter(field) for field in FILTER_FIELDS}


def build_where_clause(filters: dict[str, str | None]) -> tuple[str, dict[str, str]]:
    """Create a parameterized WHERE clause using only fixed filter column names."""
    parts: list[str] = []
    parameters: dict[str, str] = {}
    for field, value in filters.items():
        if value is not None:
            parts.append(f"{field} = :{field}")
            parameters[field] = value
    return (f"WHERE {' AND '.join(parts)}" if parts else ""), parameters


def fetch_rows(statement: str, parameters: dict[str, str]) -> list[dict]:
    """Execute a read-only query and convert SQLAlchemy mappings to dictionaries."""
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(text(statement), parameters).mappings()]


def latest_updated_at(table_name: str) -> str | None:
    """Return the latest Spark aggregation timestamp for a fixed summary table."""
    with engine.connect() as connection:
        updated_at = connection.execute(
            text(f"SELECT MAX(updated_at) FROM {table_name}")
        ).scalar_one()
    if updated_at is None:
        return None
    if isinstance(updated_at, datetime) and updated_at.tzinfo is None:
        return updated_at.isoformat(timespec="seconds") + "+08:00"
    return updated_at.isoformat(timespec="seconds")


def as_int(value: int | None) -> int:
    """Serialize nullable aggregate counts as integers."""
    return int(value or 0)


def as_number(value: Decimal | float | int | None, digits: int = 2) -> float | None:
    """Serialize nullable DECIMAL aggregates as JSON numbers."""
    return None if value is None else round(float(value), digits)


def ratio(numerator: int | Decimal | None, denominator: int | Decimal | None) -> float | None:
    """Calculate a nullable ratio with a consistent four-decimal response precision."""
    if not denominator:
        return None
    return round(float(numerator or 0) / float(denominator), 4)


def average(total: Decimal | float | None, count: int | None) -> float | None:
    """Calculate an average from a stored aggregate total and count."""
    if total is None or not count:
        return None
    return round(float(total) / int(count), 2)


def success_response(
    data: list[dict] | dict, filters: dict[str, str | None], table_name: str
):
    """Return data in the common dashboard response envelope."""
    return jsonify(
        {
            "code": 0,
            "message": "success",
            "data": data,
            "filters": filters,
            "updated_at": latest_updated_at(table_name),
        }
    )


@patient_bp.get("/age-gender")
def get_age_gender():
    """Return age and gender discharge counts for the current filter scope."""
    try:
        filters = read_global_filters()
        where_clause, parameters = build_where_clause(filters)
        rows = fetch_rows(
            f"""
            SELECT age_group, age_group_sort, gender, SUM(discharge_count) AS discharge_count
            FROM patient_age_gender_summary
            {where_clause}
            GROUP BY age_group, age_group_sort, gender
            ORDER BY age_group_sort IS NULL, age_group_sort, gender
            """,
            parameters,
        )
        total = sum(as_int(row["discharge_count"]) for row in rows)
        data = [
            {
                "age_group": row["age_group"],
                "age_group_sort": row["age_group_sort"],
                "gender": row["gender"],
                "discharge_count": as_int(row["discharge_count"]),
                "discharge_ratio": ratio(row["discharge_count"], total),
            }
            for row in rows
        ]
        return success_response(data, filters, "patient_age_gender_summary")
    except ValueError as error:
        return error_response(str(error), 400)


@patient_bp.get("/payment")
def get_payment():
    """Return payment structure and cost metrics for the current filter scope."""
    try:
        filters = read_global_filters()
        where_clause, parameters = build_where_clause(filters)
        rows = fetch_rows(
            f"""
            SELECT payment_typology_1,
                   SUM(discharge_count) AS discharge_count,
                   SUM(total_charges_sum) AS total_charges,
                   SUM(total_costs_sum) AS total_costs
            FROM patient_payment_summary
            {where_clause}
            GROUP BY payment_typology_1
            ORDER BY discharge_count DESC, payment_typology_1
            """,
            parameters,
        )
        total = sum(as_int(row["discharge_count"]) for row in rows)
        data = [
            {
                "payment_typology_1": row["payment_typology_1"],
                "discharge_count": as_int(row["discharge_count"]),
                "discharge_ratio": ratio(row["discharge_count"], total),
                "total_charges": as_number(row["total_charges"]),
                "total_costs": as_number(row["total_costs"]),
                "average_charge": average(row["total_charges"], row["discharge_count"]),
                "average_cost": average(row["total_costs"], row["discharge_count"]),
            }
            for row in rows
        ]
        return success_response(data, filters, "patient_payment_summary")
    except ValueError as error:
        return error_response(str(error), 400)


@patient_bp.get("/disposition")
def get_disposition():
    """Return the most common patient dispositions for the current filter scope."""
    try:
        filters = read_global_filters()
        raw_limit = read_optional_parameter("limit")
        limit = 10 if raw_limit is None else int(raw_limit)
        if not 1 <= limit <= 20:
            raise ValueError("limit must be between 1 and 20")

        where_clause, parameters = build_where_clause(filters)
        rows = fetch_rows(
            f"""
            SELECT patient_disposition,
                   SUM(discharge_count) AS discharge_count,
                   SUM(length_of_stay_sum) AS length_of_stay_sum,
                   SUM(total_charges_sum) AS total_charges,
                   SUM(total_costs_sum) AS total_costs
            FROM patient_disposition_summary
            {where_clause}
            GROUP BY patient_disposition
            ORDER BY discharge_count DESC, patient_disposition
            """,
            parameters,
        )
        total = sum(as_int(row["discharge_count"]) for row in rows)
        data = [
            {
                "patient_disposition": row["patient_disposition"],
                "discharge_count": as_int(row["discharge_count"]),
                "discharge_ratio": ratio(row["discharge_count"], total),
                "average_length_of_stay": average(
                    row["length_of_stay_sum"], row["discharge_count"]
                ),
                "total_charges": as_number(row["total_charges"]),
                "total_costs": as_number(row["total_costs"]),
                "average_charge": average(row["total_charges"], row["discharge_count"]),
                "average_cost": average(row["total_costs"], row["discharge_count"]),
            }
            for row in rows[:limit]
        ]
        return success_response(data, filters, "patient_disposition_summary")
    except (TypeError, ValueError) as error:
        return error_response(str(error), 400)


@patient_bp.get("/admission-emergency")
def get_admission_emergency():
    """Return admission-type and emergency-department structure data."""
    try:
        filters = read_global_filters()
        where_clause, parameters = build_where_clause(filters)
        rows = fetch_rows(
            f"""
            SELECT type_of_admission,
                   emergency_department_indicator,
                   SUM(discharge_count) AS discharge_count,
                   SUM(length_of_stay_sum) AS length_of_stay_sum
            FROM patient_admission_emergency_summary
            {where_clause}
            GROUP BY type_of_admission, emergency_department_indicator
            ORDER BY type_of_admission, emergency_department_indicator
            """,
            parameters,
        )
        total = sum(as_int(row["discharge_count"]) for row in rows)
        data = [
            {
                "type_of_admission": row["type_of_admission"],
                "emergency_department_indicator": row[
                    "emergency_department_indicator"
                ],
                "discharge_count": as_int(row["discharge_count"]),
                "discharge_ratio": ratio(row["discharge_count"], total),
                "average_length_of_stay": average(
                    row["length_of_stay_sum"], row["discharge_count"]
                ),
            }
            for row in rows
        ]
        return success_response(data, filters, "patient_admission_emergency_summary")
    except ValueError as error:
        return error_response(str(error), 400)
