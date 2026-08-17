"""Disease and risk endpoints for the BI dashboard right panel."""

from __future__ import annotations

from flask import Blueprint, jsonify

from src.routes.filters import error_response, read_optional_parameter
from src.routes.patient import (
    as_int,
    as_number,
    average,
    build_where_clause,
    fetch_rows,
    latest_updated_at,
    ratio,
    read_global_filters,
    success_response,
)


disease_bp = Blueprint("disease", __name__, url_prefix="/api/dashboard/disease")


def read_limit(default: int, maximum: int) -> int:
    """Read and validate a chart Top N limit."""
    raw_value = read_optional_parameter("limit")
    value = default if raw_value is None else int(raw_value)
    if not 1 <= value <= maximum:
        raise ValueError(f"limit must be between 1 and {maximum}")
    return value


def aggregate_rows(table_name: str, select_clause: str, group_clause: str, filters: dict):
    """Aggregate a fixed summary table under the shared dashboard filters."""
    where_clause, parameters = build_where_clause(filters)
    rows = fetch_rows(
        f"""
        SELECT {select_clause},
               SUM(discharge_count) AS discharge_count,
               SUM(length_of_stay_sum) AS length_of_stay_sum,
               SUM(total_charges_sum) AS total_charges,
               SUM(total_costs_sum) AS total_costs
        FROM {table_name}
        {where_clause}
        GROUP BY {group_clause}
        """,
        parameters,
    )
    return rows


def serialize_disease_row(row: dict, code_field: str, description_field: str) -> dict:
    """Serialize a disease aggregate into the common chart data shape."""
    discharge_count = as_int(row["discharge_count"])
    return {
        code_field: row[code_field],
        description_field: row[description_field],
        "discharge_count": discharge_count,
        "average_length_of_stay": average(row["length_of_stay_sum"], discharge_count),
        "total_charges": as_number(row["total_charges"]),
        "total_costs": as_number(row["total_costs"]),
    }


@disease_bp.get("/systems")
def get_disease_systems():
    """Return APR MDC disease-system distribution for the selected scope."""
    try:
        filters = read_global_filters()
        rows = aggregate_rows(
            "disease_system_summary",
            "apr_mdc_code, MAX(apr_mdc_description) AS apr_mdc_description",
            "apr_mdc_code",
            filters,
        )
        total = sum(as_int(row["discharge_count"]) for row in rows)
        data = []
        for row in sorted(rows, key=lambda item: (-as_int(item["discharge_count"]), item["apr_mdc_code"] or "")):
            item = serialize_disease_row(row, "apr_mdc_code", "apr_mdc_description")
            item["discharge_ratio"] = ratio(row["discharge_count"], total)
            data.append(item)
        return success_response(data, filters, "disease_system_summary")
    except ValueError as error:
        return error_response(str(error), 400)


@disease_bp.get("/top-diagnoses")
def get_top_diagnoses():
    """Return the most common CCSR diagnoses for the selected scope."""
    try:
        filters = read_global_filters()
        limit = read_limit(10, 30)
        rows = aggregate_rows(
            "diagnosis_summary",
            "ccsr_diagnosis_code, MAX(ccsr_diagnosis_description) AS ccsr_diagnosis_description",
            "ccsr_diagnosis_code",
            filters,
        )
        total = sum(as_int(row["discharge_count"]) for row in rows)
        ordered_rows = sorted(
            rows,
            key=lambda item: (-as_int(item["discharge_count"]), item["ccsr_diagnosis_code"] or ""),
        )
        data = []
        for row in ordered_rows[:limit]:
            item = serialize_disease_row(
                row, "ccsr_diagnosis_code", "ccsr_diagnosis_description"
            )
            item["discharge_ratio"] = ratio(row["discharge_count"], total)
            data.append(item)
        return success_response(data, filters, "diagnosis_summary")
    except (TypeError, ValueError) as error:
        return error_response(str(error), 400)


@disease_bp.get("/risk")
def get_patient_risk():
    """Return APR severity distribution for the selected scope."""
    try:
        filters = read_global_filters()
        rows = aggregate_rows(
            "patient_risk_summary",
            "apr_severity_code, MAX(apr_severity_description) AS apr_severity_description",
            "apr_severity_code",
            filters,
        )
        # The dashboard chart contains the four valid severity levels only.
        rows = [row for row in rows if row["apr_severity_code"] is not None]
        total = sum(as_int(row["discharge_count"]) for row in rows)
        data = []
        for row in sorted(
            rows,
            key=lambda item: (
                item["apr_severity_code"] or 0,
            ),
        ):
            discharge_count = as_int(row["discharge_count"])
            data.append(
                {
                    "apr_severity_code": row["apr_severity_code"],
                    "apr_severity_description": row["apr_severity_description"],
                    "discharge_count": discharge_count,
                    "discharge_ratio": ratio(row["discharge_count"], total),
                    "average_length_of_stay": average(
                        row["length_of_stay_sum"], discharge_count
                    ),
                    "total_charges": as_number(row["total_charges"]),
                    "total_costs": as_number(row["total_costs"]),
                }
            )
        return success_response(data, filters, "patient_risk_summary")
    except ValueError as error:
        return error_response(str(error), 400)


def read_drilldown_parameters() -> tuple[str, str | None, str | None]:
    """Validate the requested drilldown depth and its required parent codes."""
    level = read_optional_parameter("level")
    mdc_code = read_optional_parameter("apr_mdc_code")
    drg_code = read_optional_parameter("apr_drg_code")
    if level not in {"mdc", "drg", "ccsr"}:
        raise ValueError("level must be mdc, drg, or ccsr")
    if level in {"drg", "ccsr"} and mdc_code is None:
        raise ValueError("apr_mdc_code is required for this level")
    if level == "ccsr" and drg_code is None:
        raise ValueError("apr_drg_code is required for level ccsr")
    return level, mdc_code, drg_code


def read_drilldown_rows(
    level: str,
    filters: dict[str, str | None],
    mdc_code: str | None,
    drg_code: str | None,
) -> list[dict]:
    """Query one drilldown level using the fixed MDC, DRG, CCSR hierarchy."""
    where_clause, parameters = build_where_clause(filters)
    conditions = [where_clause.removeprefix("WHERE ")] if where_clause else []
    if mdc_code is not None:
        conditions.append("apr_mdc_code = :apr_mdc_code")
        parameters["apr_mdc_code"] = mdc_code
    if drg_code is not None:
        conditions.append("apr_drg_code = :apr_drg_code")
        parameters["apr_drg_code"] = drg_code
    effective_where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    level_specification = {
        "mdc": (
            "apr_mdc_code AS code, MAX(apr_mdc_description) AS description",
            "apr_mdc_code",
        ),
        "drg": (
            "apr_drg_code AS code, MAX(apr_drg_description) AS description",
            "apr_drg_code",
        ),
        "ccsr": (
            "ccsr_diagnosis_code AS code, MAX(ccsr_diagnosis_description) AS description",
            "ccsr_diagnosis_code",
        ),
    }
    select_clause, group_clause = level_specification[level]
    return fetch_rows(
        f"""
        SELECT {select_clause},
               SUM(discharge_count) AS discharge_count,
               SUM(length_of_stay_sum) AS length_of_stay_sum,
               SUM(total_charges_sum) AS total_charges,
               SUM(total_costs_sum) AS total_costs
        FROM disease_drilldown_summary
        {effective_where}
        GROUP BY {group_clause}
        ORDER BY discharge_count DESC, code ASC
        """,
        parameters,
    )


def build_breadcrumb(mdc_code: str | None, drg_code: str | None, filters: dict) -> list[dict]:
    """Return display labels for the selected MDC and DRG drilldown parents."""
    breadcrumb: list[dict] = []
    if mdc_code is None:
        return breadcrumb

    where_clause, parameters = build_where_clause(filters)
    conditions = [where_clause.removeprefix("WHERE ")] if where_clause else []
    conditions.append("apr_mdc_code = :apr_mdc_code")
    parameters["apr_mdc_code"] = mdc_code
    effective_where = f"WHERE {' AND '.join(conditions)}"
    mdc = fetch_rows(
        f"""
        SELECT MAX(apr_mdc_description) AS description
        FROM disease_drilldown_summary
        {effective_where}
        """,
        parameters,
    )[0]
    breadcrumb.append(
        {"level": "mdc", "code": mdc_code, "description": mdc["description"]}
    )

    if drg_code is not None:
        conditions.append("apr_drg_code = :apr_drg_code")
        parameters["apr_drg_code"] = drg_code
        effective_where = f"WHERE {' AND '.join(conditions)}"
        drg = fetch_rows(
            f"""
            SELECT MAX(apr_drg_description) AS description
            FROM disease_drilldown_summary
            {effective_where}
            """,
            parameters,
        )[0]
        breadcrumb.append(
            {"level": "drg", "code": drg_code, "description": drg["description"]}
        )
    return breadcrumb


@disease_bp.get("/drilldown")
def get_disease_drilldown():
    """Return one level of the MDC-to-DRG-to-CCSR disease hierarchy."""
    try:
        filters = read_global_filters()
        level, mdc_code, drg_code = read_drilldown_parameters()
        rows = read_drilldown_rows(level, filters, mdc_code, drg_code)
        data = []
        for row in rows:
            discharge_count = as_int(row["discharge_count"])
            data.append(
                {
                    "code": row["code"],
                    "description": row["description"],
                    "discharge_count": discharge_count,
                    "total_charges": as_number(row["total_charges"]),
                    "total_costs": as_number(row["total_costs"]),
                    "average_length_of_stay": average(
                        row["length_of_stay_sum"], discharge_count
                    ),
                }
            )
        return jsonify(
            {
                "code": 0,
                "message": "success",
                "data": data,
                "filters": filters,
                "breadcrumb": build_breadcrumb(mdc_code, drg_code, filters),
                "updated_at": latest_updated_at("disease_drilldown_summary"),
            }
        )
    except ValueError as error:
        return error_response(str(error), 400)
