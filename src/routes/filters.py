"""Global filter candidate endpoints for the BI dashboard."""

from __future__ import annotations

from datetime import datetime

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.database import engine


filters_bp = Blueprint("filters", __name__, url_prefix="/api/filters")
SUMMARY_TABLE = "hospital_operation_summary"
FILTER_FIELDS = ("hospital_service_area", "hospital_county", "facility_name")


def read_optional_parameter(name: str) -> str | None:
    """Return a normalized optional filter value or reject invalid input."""
    value = request.args.get(name)
    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        return None
    if "\x00" in normalized or len(normalized) > 255:
        raise ValueError(f"invalid {name}")
    return normalized


def latest_updated_at() -> str | None:
    """Return the latest Spark aggregation timestamp from the filter source table."""
    with engine.connect() as connection:
        updated_at = connection.execute(
            text(f"SELECT MAX(updated_at) FROM {SUMMARY_TABLE}")
        ).scalar_one()

    if updated_at is None:
        return None
    if isinstance(updated_at, datetime) and updated_at.tzinfo is None:
        return updated_at.isoformat(timespec="seconds") + "+08:00"
    return updated_at.isoformat(timespec="seconds")


def success_response(data: list[dict[str, str]], filters: dict[str, str | None]):
    """Build the standard successful API response."""
    return jsonify(
        {
            "code": 0,
            "message": "success",
            "data": data,
            "filters": filters,
            "updated_at": latest_updated_at(),
        }
    )


def query_values(column: str, conditions: dict[str, str | None]) -> list[dict[str, str]]:
    """Fetch distinct non-empty values with bound query parameters."""
    if column not in FILTER_FIELDS:
        raise ValueError("unsupported filter column")

    where_parts = [f"{column} IS NOT NULL", f"TRIM({column}) <> ''"]
    parameters: dict[str, str] = {}
    for field, value in conditions.items():
        if value is not None:
            where_parts.append(f"{field} = :{field}")
            parameters[field] = value

    statement = text(
        f"SELECT DISTINCT {column} "
        f"FROM {SUMMARY_TABLE} "
        f"WHERE {' AND '.join(where_parts)} "
        f"ORDER BY {column} ASC"
    )
    with engine.connect() as connection:
        values = connection.execute(statement, parameters).scalars().all()
    return [{column: value} for value in values]


@filters_bp.get("/areas")
def get_areas():
    """Return all available hospital service areas."""
    return success_response(
        query_values("hospital_service_area", {}),
        {field: None for field in FILTER_FIELDS},
    )


@filters_bp.get("/counties")
def get_counties():
    """Return counties, optionally restricted to one service area."""
    try:
        area = read_optional_parameter("hospital_service_area")
        return success_response(
            query_values("hospital_county", {"hospital_service_area": area}),
            {
                "hospital_service_area": area,
                "hospital_county": None,
                "facility_name": None,
            },
        )
    except ValueError as error:
        return error_response(str(error), 400)


@filters_bp.get("/facilities")
def get_facilities():
    """Return facilities, optionally restricted to service area and county."""
    try:
        area = read_optional_parameter("hospital_service_area")
        county = read_optional_parameter("hospital_county")
        return success_response(
            query_values(
                "facility_name",
                {
                    "hospital_service_area": area,
                    "hospital_county": county,
                },
            ),
            {
                "hospital_service_area": area,
                "hospital_county": county,
                "facility_name": None,
            },
        )
    except ValueError as error:
        return error_response(str(error), 400)


def error_response(message: str, status_code: int):
    """Build the standard failed API response."""
    return jsonify({"code": 40001, "message": message, "data": None}), status_code


@filters_bp.app_errorhandler(SQLAlchemyError)
def handle_database_error(error: SQLAlchemyError):
    """Prevent database details from leaking through the API."""
    current_app.logger.exception("Database query failed", exc_info=error)
    return jsonify({"code": 50001, "message": "database query failed", "data": None}), 500
