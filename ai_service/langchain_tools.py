"""LangChain registrations for the service-owned whitelist tools."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import StructuredTool

from ai_service.tools import TOOLS, call_tool


TOOL_DESCRIPTIONS = {
    "get_kpi": "查询医院数、出院量、收费、成本与急诊占比等总体运营指标。",
    "get_age_gender": "查询患者年龄和性别结构。",
    "get_payment": "查询主要支付方式分布。",
    "get_disposition": "查询离院去向排名。",
    "get_admission_emergency": "查询入院类型与急诊结构。",
    "get_hospital_ranking": "查询医院运营排名。",
    "get_disease_systems": "查询疾病系统分布。",
    "get_top_diagnoses": "查询高发疾病排名。",
    "get_severity": "查询病情严重程度分布。",
}


def _make_coroutine(tool_name: str):
    async def run() -> Any:
        return await call_tool(tool_name)

    return run


LANGCHAIN_TOOLS = [
    StructuredTool.from_function(
        coroutine=_make_coroutine(name),
        name=name,
        description=TOOL_DESCRIPTIONS[name],
    )
    for name in TOOLS
]
