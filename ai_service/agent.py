"""Intent routing, whitelist tool execution, and fact-based reply generation."""

from __future__ import annotations

from typing import Any

from ai_service.config import settings
from ai_service.langchain_tools import LANGCHAIN_TOOLS
from ai_service.prompts import SYSTEM_PROMPT
from ai_service.schemas import ChatData, ToolCall
from ai_service.tools import ToolRequestError, call_tool


INTENT_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("get_top_diagnoses", ("高发疾病", "常见疾病", "具体疾病", "诊断")),
    ("get_disease_systems", ("疾病系统", "疾病类型", "mdc")),
    ("get_severity", ("严重程度", "病情", "轻重")),
    ("get_hospital_ranking", ("医院排名", "医院排行", "哪家医院", "排名")),
    ("get_age_gender", ("年龄", "性别", "男女", "患者结构")),
    ("get_payment", ("支付", "医保", "medicare", "medicaid", "保险")),
    ("get_disposition", ("离院", "出院去向", "回家", "死亡")),
    ("get_kpi", ("住院量", "出院量", "收费", "成本", "医院数", "急诊占比", "急诊患者", "概览", "指标")),
    ("get_admission_emergency", ("入院", "急诊结构", "emergency")),
)


def route_intent(message: str) -> str | None:
    """Select exactly one approved tool for phase one."""

    normalized = message.lower().strip()
    for tool_name, keywords in INTENT_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            return tool_name
    return None


def _number(value: Any, digits: int = 0) -> str:
    try:
        return f"{float(value):,.{digits}f}"
    except (TypeError, ValueError):
        return "--"


def _percentage(value: Any) -> str:
    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return "--"


def build_deterministic_reply(tool_name: str, result: Any) -> str:
    """Build a factual fallback reply when no external LLM is configured."""

    if tool_name == "get_kpi" and isinstance(result, dict):
        return (
            f"当前范围内共有 {_number(result.get('hospital_count'))} 家医院、"
            f"{_number(result.get('discharge_count'))} 条出院记录，"
            f"急诊出院记录占比为 {_percentage(result.get('emergency_ratio'))}。"
        )
    if tool_name == "get_age_gender" and result:
        leading = max(result, key=lambda item: item.get("discharge_count", 0))
        return f"出院记录最多的是 {leading.get('age_group', '--')} 年龄组的 {leading.get('gender', '--')} 性患者，共 {_number(leading.get('discharge_count'))} 条。"
    if tool_name == "get_payment" and result:
        leading = max(result, key=lambda item: item.get("discharge_count", 0))
        return f"主要支付方式中，{leading.get('payment_typology_1', '--')} 占比最高，共 {_number(leading.get('discharge_count'))} 条出院记录。"
    if tool_name == "get_disposition" and result:
        leading = max(result, key=lambda item: item.get("discharge_count", 0))
        return f"最常见的离院去向是 {leading.get('patient_disposition', '--')}，共 {_number(leading.get('discharge_count'))} 条记录。"
    if tool_name == "get_admission_emergency" and result:
        total = sum(item.get("discharge_count", 0) or 0 for item in result)
        emergency = sum(item.get("discharge_count", 0) or 0 for item in result if item.get("emergency_department_indicator") == "Y")
        ratio = emergency / total if total else 0
        return f"当前范围共有 {_number(total)} 条入院记录，其中急诊入院 {_number(emergency)} 条，占 {_percentage(ratio)}。"
    if tool_name == "get_hospital_ranking" and result:
        leading = result[0]
        return f"按当前默认出院量排序，{leading.get('facility_name', '--')} 排名第一，出院量为 {_number(leading.get('discharge_count'))} 条。"
    if tool_name == "get_disease_systems" and result:
        leading = max(result, key=lambda item: item.get("discharge_count", 0))
        return f"住院量最高的疾病系统为 {leading.get('apr_mdc_description', leading.get('apr_mdc_code', '--'))}，共有 {_number(leading.get('discharge_count'))} 条出院记录。"
    if tool_name == "get_top_diagnoses" and result:
        leading = result[0]
        return f"高发疾病排名第一的是 {leading.get('ccsr_diagnosis_description', leading.get('ccsr_diagnosis_code', '--'))}，共有 {_number(leading.get('discharge_count'))} 条出院记录。"
    if tool_name == "get_severity" and result:
        leading = max(result, key=lambda item: item.get("discharge_count", 0))
        return f"病情严重程度以 {leading.get('apr_severity_description', '--')} 为主，共 {_number(leading.get('discharge_count'))} 条出院记录。"
    return "已完成数据分析，但当前结果不足以生成摘要。"


async def _rewrite_with_llm(question: str, draft: str, result: Any) -> str:
    """Optionally improve wording through a compatible OpenAI-style model endpoint."""

    if not (settings.llm_api_key and settings.llm_model):
        return draft

    try:
        from langchain_openai import ChatOpenAI

        model = ChatOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url or None,
            model=settings.llm_model,
            temperature=0,
            timeout=settings.request_timeout_seconds,
        )
        prompt = f"{SYSTEM_PROMPT}\n\n用户问题：{question}\n工具结果：{result}\n\n初步摘要：{draft}\n请仅基于工具结果润色为一段简洁中文回答。"
        response = await model.ainvoke(prompt)
        content = str(response.content).strip()
        return content or draft
    except Exception:
        return draft


async def answer_question(message: str) -> ChatData:
    """Execute one safe, auditable analysis request for the phase-one sidebar."""

    # Referencing the registry ensures all callable names remain the registered whitelist.
    registered_names = {tool.name for tool in LANGCHAIN_TOOLS}
    tool_name = route_intent(message)
    if tool_name not in registered_names:
        tool_name = None
    if tool_name is None:
        return ChatData(
            reply="我目前可以回答医院运营、急诊、患者年龄与性别、支付方式、离院去向、疾病系统、高发疾病和病情严重程度相关问题。",
            tool_calls=[],
        )

    try:
        result = await call_tool(tool_name)
        draft = build_deterministic_reply(tool_name, result)
        reply = await _rewrite_with_llm(message, draft, result)
        return ChatData(reply=reply, tool_calls=[ToolCall(name=tool_name, status="success")])
    except ToolRequestError:
        return ChatData(
            reply="暂时无法完成本次分析，请确认 Flask 分析服务正在运行后重试。",
            tool_calls=[ToolCall(name=tool_name, status="failed")],
        )
