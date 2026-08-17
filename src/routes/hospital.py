"""Hospital operation endpoints for the BI dashboard center panel."""

from __future__ import annotations

from flask import Blueprint, request

from src.routes.filters import error_response, read_optional_parameter
from src.routes.patient import (
    as_int,
    as_number,
    average,
    build_where_clause,
    fetch_rows,
    ratio,
    read_global_filters,
    success_response,
)


hospital_bp = Blueprint("hospital", __name__, url_prefix="/api/dashboard")
SUMMARY_TABLE = "hospital_operation_summary"
SORT_EXPRESSIONS = {
    "discharge_count": "discharge_count",
    "total_charges": "total_charges",
    "average_length_of_stay": "average_length_of_stay",
    "average_cost": "average_cost",
}


def read_pagination_parameter(name: str, default: int, minimum: int, maximum: int) -> int:
    """Read and validate a positive integer pagination parameter."""
    raw_value = read_optional_parameter(name)
    value = default if raw_value is None else int(raw_value)
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def read_sort_parameters() -> tuple[str, str]:
    """Read sorting controls through a fixed SQL expression whitelist."""
    sort_by = read_optional_parameter("sort_by") or "discharge_count"
    order = (read_optional_parameter("order") or "desc").lower()
    if sort_by not in SORT_EXPRESSIONS:
        raise ValueError("invalid sort_by")
    if order not in {"asc", "desc"}:
        raise ValueError("order must be asc or desc")
    return SORT_EXPRESSIONS[sort_by], order.upper()


def grouped_hospital_select(where_clause: str) -> str:
    """Return the reusable hospital aggregation query without ordering or pagination."""
    return f"""
        SELECT hospital_service_area,
               hospital_county,
               facility_name,
               SUM(discharge_count) AS discharge_count,
               SUM(length_of_stay_sum) AS length_of_stay_sum,
               SUM(total_charges_sum) AS total_charges,
               SUM(total_costs_sum) AS total_costs,
               SUM(emergency_yes_count) AS emergency_yes_count,
               SUM(emergency_known_count) AS emergency_known_count,
               SUM(length_of_stay_sum) / NULLIF(SUM(discharge_count), 0) AS average_length_of_stay,
               SUM(total_costs_sum) / NULLIF(SUM(discharge_count), 0) AS average_cost,
               SUM(emergency_yes_count) / NULLIF(SUM(emergency_known_count), 0) AS emergency_ratio
        FROM {SUMMARY_TABLE}
        {where_clause}
        GROUP BY hospital_service_area, hospital_county, facility_name
    """


def serialize_hospital_row(row: dict, rank: int | None = None) -> dict:
    """Convert one hospital aggregate row to the public API contract."""
    result = {
        "facility_name": row["facility_name"],
        "hospital_county": row["hospital_county"],
        "hospital_service_area": row["hospital_service_area"],
        "discharge_count": as_int(row["discharge_count"]),
        "total_charges": as_number(row["total_charges"]),
        "total_costs": as_number(row["total_costs"]),
        "average_length_of_stay": as_number(row["average_length_of_stay"]),
        "average_cost": as_number(row["average_cost"]),
        "emergency_ratio": as_number(row["emergency_ratio"], 4),
    }
    if rank is not None:
        result = {"rank": rank, **result}
    return result


@hospital_bp.get("/kpi")
def get_kpi():
    """Return hospital operation KPI cards for the active dashboard scope."""
    try:
        filters = read_global_filters()
        where_clause, parameters = build_where_clause(filters)
        row = fetch_rows(
            f"""
            SELECT COUNT(DISTINCT facility_name) AS hospital_count,
                   SUM(discharge_count) AS discharge_count,
                   SUM(length_of_stay_sum) AS length_of_stay_sum,
                   SUM(total_charges_sum) AS total_charges,
                   SUM(total_costs_sum) AS total_costs,
                   SUM(emergency_yes_count) AS emergency_yes_count,
                   SUM(emergency_known_count) AS emergency_known_count,
                   SUM(emergency_charges_sum) AS emergency_charges,
                   SUM(non_emergency_charges_sum) AS non_emergency_charges,
                   SUM(emergency_costs_sum) AS emergency_costs,
                   SUM(non_emergency_costs_sum) AS non_emergency_costs
            FROM {SUMMARY_TABLE}
            {where_clause}
            """,
            parameters,
        )[0]
        discharge_count = as_int(row["discharge_count"])
        data = {
            "hospital_count": as_int(row["hospital_count"]),
            "discharge_count": discharge_count,
            "average_length_of_stay": average(row["length_of_stay_sum"], discharge_count),
            "total_charges": as_number(row["total_charges"]),
            "total_costs": as_number(row["total_costs"]),
            "average_charge": average(row["total_charges"], discharge_count),
            "average_cost": average(row["total_costs"], discharge_count),
            "emergency_ratio": ratio(
                row["emergency_yes_count"], row["emergency_known_count"]
            ),
            "emergency_charges": as_number(row["emergency_charges"]),
            "non_emergency_charges": as_number(row["non_emergency_charges"]),
            "emergency_costs": as_number(row["emergency_costs"]),
            "non_emergency_costs": as_number(row["non_emergency_costs"]),
        }
        return success_response(data, filters, SUMMARY_TABLE)
    except ValueError as error:
        return error_response(str(error), 400)


@hospital_bp.get("/hospital/resources")
def get_hospital_resources():
    """Return one aggregate row per hospital for the resource and cost bubble chart."""
    try:
        filters = read_global_filters()
        where_clause, parameters = build_where_clause(filters)
        rows = fetch_rows(
            f"""
            {grouped_hospital_select(where_clause)}
            ORDER BY discharge_count DESC, facility_name
            """,
            parameters,
        )
        return success_response(
            [serialize_hospital_row(row) for row in rows], filters, SUMMARY_TABLE
        )
    except ValueError as error:
        return error_response(str(error), 400)


@hospital_bp.get("/hospital/ranking")
def get_hospital_ranking():
    """Return ranked hospitals for the selected operational metric."""
    try:
        filters = read_global_filters()
        sort_expression, order = read_sort_parameters()
        limit = read_pagination_parameter("limit", 10, 1, 50)
        where_clause, parameters = build_where_clause(filters)
        parameters["limit"] = limit
        rows = fetch_rows(
            f"""
            {grouped_hospital_select(where_clause)}
            ORDER BY {sort_expression} {order}, facility_name ASC
            LIMIT :limit
            """,
            parameters,
        )
        return success_response(
            [serialize_hospital_row(row, index) for index, row in enumerate(rows, 1)],
            filters,
            SUMMARY_TABLE,
        )
    except (TypeError, ValueError) as error:
        return error_response(str(error), 400)


@hospital_bp.get("/hospital/comparison")
def get_hospital_comparison():
    """Return a paginated and sortable hospital comparison table."""
    try:
        filters = read_global_filters()
        sort_expression, order = read_sort_parameters()
        page = read_pagination_parameter("page", 1, 1, 100000)
        page_size = read_pagination_parameter("page_size", 20, 1, 100)
        keyword = read_optional_parameter("keyword")
        where_clause, parameters = build_where_clause(filters)

        conditions = [where_clause.removeprefix("WHERE ")] if where_clause else []
        if keyword is not None:
            conditions.append("facility_name LIKE :keyword")
            parameters["keyword"] = f"%{keyword}%"
        effective_where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        total = fetch_rows(
            f"""
            SELECT COUNT(*) AS total
            FROM (
                SELECT 1
                FROM {SUMMARY_TABLE}
                {effective_where}
                GROUP BY hospital_service_area, hospital_county, facility_name
            ) AS hospital_rows
            """,
            parameters,
        )[0]["total"]

        parameters["limit"] = page_size
        parameters["offset"] = (page - 1) * page_size
        rows = fetch_rows(
            f"""
            {grouped_hospital_select(effective_where)}
            ORDER BY {sort_expression} {order}, facility_name ASC
            LIMIT :limit OFFSET :offset
            """,
            parameters,
        )
        data = {
            "items": [serialize_hospital_row(row) for row in rows],
            "page": page,
            "page_size": page_size,
            "total": as_int(total),
        }
        return success_response(data, filters, SUMMARY_TABLE)
    except (TypeError, ValueError) as error:
        return error_response(str(error), 400)
