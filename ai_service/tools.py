"""Whitelist-only HTTP tools for the existing Flask analytics service."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Mapping

import httpx

from ai_service.config import settings


class ToolRequestError(RuntimeError):
    """Raised when an approved analytics tool cannot return valid data."""


async def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    """Call Flask with a timeout and validate the shared response envelope."""

    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.get(f"{settings.flask_api_base_url}{path}", params=params)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise ToolRequestError("医疗分析服务暂时不可用。") from error

    if not isinstance(payload, dict):
        raise ToolRequestError("医疗分析服务返回了无效响应。")
    if payload.get("code") != 0:
        raise ToolRequestError(str(payload.get("message", "医疗分析服务返回异常。")))
    return payload.get("data")


async def get_kpi() -> dict[str, Any]:
    return await _get("/dashboard/kpi")


async def get_age_gender() -> list[dict[str, Any]]:
    return await _get("/dashboard/patient/age-gender")


async def get_payment() -> list[dict[str, Any]]:
    return await _get("/dashboard/patient/payment")


async def get_disposition() -> list[dict[str, Any]]:
    return await _get("/dashboard/patient/disposition", {"limit": 10})


async def get_admission_emergency() -> list[dict[str, Any]]:
    return await _get("/dashboard/patient/admission-emergency")


async def get_medical_surgical() -> list[dict[str, Any]]:
    return await _get("/dashboard/patient/medical-surgical")


async def get_hospital_ranking() -> list[dict[str, Any]]:
    return await _get("/dashboard/hospital/ranking", {"limit": 10})


async def get_disease_systems() -> list[dict[str, Any]]:
    return await _get("/dashboard/disease/systems")


async def get_top_diagnoses() -> list[dict[str, Any]]:
    return await _get("/dashboard/disease/top-diagnoses", {"limit": 10})


async def get_severity() -> list[dict[str, Any]]:
    return await _get("/dashboard/disease/risk")


ToolFunction = Callable[[], Awaitable[Any]]

TOOLS: dict[str, ToolFunction] = {
    "get_kpi": get_kpi,
    "get_age_gender": get_age_gender,
    "get_payment": get_payment,
    "get_disposition": get_disposition,
    "get_admission_emergency": get_admission_emergency,
    "get_medical_surgical": get_medical_surgical,
    "get_hospital_ranking": get_hospital_ranking,
    "get_disease_systems": get_disease_systems,
    "get_top_diagnoses": get_top_diagnoses,
    "get_severity": get_severity,
}


async def call_tool(name: str) -> Any:
    """Run one known tool and reject all unspecified operations."""

    tool = TOOLS.get(name)
    if tool is None:
        raise ToolRequestError("未注册的数据分析工具。")
    return await tool()


REPORT_TOOL_PATHS: dict[str, tuple[str, dict[str, Any]]] = {
    "get_kpi": ("/dashboard/kpi", {}),
    "get_age_gender": ("/dashboard/patient/age-gender", {}),
    "get_payment": ("/dashboard/patient/payment", {}),
    "get_disposition": ("/dashboard/patient/disposition", {"limit": 10}),
    "get_admission_emergency": ("/dashboard/patient/admission-emergency", {}),
    "get_medical_surgical": ("/dashboard/patient/medical-surgical", {}),
    "get_hospital_ranking": ("/dashboard/hospital/ranking", {"limit": 10}),
    "get_disease_systems": ("/dashboard/disease/systems", {}),
    "get_top_diagnoses": ("/dashboard/disease/top-diagnoses", {"limit": 10}),
    "get_severity": ("/dashboard/disease/risk", {}),
}


async def call_tool_with_filters(name: str, filters: Mapping[str, str | None]) -> Any:
    """Call an approved analytics endpoint with the active dashboard scope."""

    definition = REPORT_TOOL_PATHS.get(name)
    if definition is None:
        raise ToolRequestError("未注册的报告分析工具。")
    path, extra = definition
    params: dict[str, Any] = dict(extra)
    for key in ("hospital_service_area", "hospital_county", "facility_name"):
        value = filters.get(key)
        if value:
            params[key] = value
    return await _get(path, params)
