"""LLM-first orchestration for the medical BI sidebar assistant."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from ai_service.config import settings
from ai_service.langchain_tools import LANGCHAIN_TOOLS
from ai_service.prompts import SYSTEM_PROMPT
from ai_service.schemas import ChatData, ToolCall


MAX_TOOL_CALLS = 3
TOOL_REGISTRY = {tool.name: tool for tool in LANGCHAIN_TOOLS}


def _build_model() -> ChatOpenAI:
    """Create the configured OpenAI-compatible chat model."""

    if not settings.llm_api_key or not settings.llm_model:
        raise RuntimeError("LLM configuration is missing")

    return ChatOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url or None,
        model=settings.llm_model,
        temperature=0,
        timeout=settings.request_timeout_seconds,
    )


def _content_to_text(content: Any) -> str:
    """Normalize provider-specific message content to non-empty plain text."""

    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        text_parts = [
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in content
        ]
        return "".join(str(part) for part in text_parts).strip()
    return str(content or "").strip()


def _tool_result_message(tool_call_id: str, tool_name: str, result: Any, status: str) -> ToolMessage:
    """Pass actual tool output back to the model without trusting user input."""

    payload = {"status": status, "data": result}
    return ToolMessage(
        content=json.dumps(payload, ensure_ascii=False, default=str),
        name=tool_name,
        tool_call_id=tool_call_id,
        status="success" if status == "success" else "error",
    )


async def answer_question(message: str) -> ChatData:
    """Let the model decide on whitelist tool use, then generate the final reply."""

    try:
        model = _build_model()
        tool_enabled_model = model.bind_tools(LANGCHAIN_TOOLS)
        messages: list[Any] = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=message)]
        initial_response = await tool_enabled_model.ainvoke(messages)
    except Exception:
        # This is an operational status message, not an analytical conclusion.
        return ChatData(
            reply="智能助手暂时不可用，请检查大模型配置和网络连接后重试。",
            tool_calls=[],
        )

    messages.append(initial_response)
    requested_calls = list(getattr(initial_response, "tool_calls", []) or [])
    tool_calls: list[ToolCall] = []

    for requested_call in requested_calls[:MAX_TOOL_CALLS]:
        tool_name = str(requested_call.get("name", ""))
        tool_call_id = str(requested_call.get("id", ""))
        tool = TOOL_REGISTRY.get(tool_name)

        if not tool or not tool_call_id:
            continue

        try:
            # Registered tools have an empty argument schema. The service owns both
            # the registry and the Flask URL, so user text cannot select an endpoint.
            result = await tool.ainvoke({})
            tool_calls.append(ToolCall(name=tool_name, status="success"))
            messages.append(_tool_result_message(tool_call_id, tool_name, result, "success"))
        except Exception:
            tool_calls.append(ToolCall(name=tool_name, status="failed"))
            messages.append(
                _tool_result_message(
                    tool_call_id,
                    tool_name,
                    {"message": "The requested analytics service is unavailable."},
                    "failed",
                )
            )

    if not requested_calls:
        reply = _content_to_text(initial_response.content)
        return ChatData(
            reply=reply or "我只能协助分析本平台的住院数据，请换一种方式描述你的问题。",
            tool_calls=[],
        )

    try:
        final_response = await model.ainvoke(messages)
        reply = _content_to_text(final_response.content)
    except Exception:
        reply = "分析数据已获取，但智能摘要暂时不可用，请稍后重试。"

    if not reply:
        reply = "本次分析未生成可展示的文字结论。"
    return ChatData(reply=reply, tool_calls=tool_calls)


async def stream_answer_question(message: str) -> AsyncIterator[dict[str, Any]]:
    """Yield model reply chunks and audited tool calls for an SSE response."""

    try:
        model = _build_model()
        tool_enabled_model = model.bind_tools(LANGCHAIN_TOOLS)
        base_messages: list[Any] = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=message)]
        initial_response = await tool_enabled_model.ainvoke(base_messages)
    except Exception:
        yield {"event": "error", "data": {"message": "智能助手暂时不可用，请检查大模型配置和网络连接后重试。"}}
        return

    messages = [*base_messages, initial_response]
    requested_calls = list(getattr(initial_response, "tool_calls", []) or [])
    tool_calls: list[ToolCall] = []

    for requested_call in requested_calls[:MAX_TOOL_CALLS]:
        tool_name = str(requested_call.get("name", ""))
        tool_call_id = str(requested_call.get("id", ""))
        tool = TOOL_REGISTRY.get(tool_name)
        if not tool or not tool_call_id:
            continue
        try:
            result = await tool.ainvoke({})
            tool_calls.append(ToolCall(name=tool_name, status="success"))
            messages.append(_tool_result_message(tool_call_id, tool_name, result, "success"))
        except Exception:
            tool_calls.append(ToolCall(name=tool_name, status="failed"))
            messages.append(
                _tool_result_message(
                    tool_call_id,
                    tool_name,
                    {"message": "The requested analytics service is unavailable."},
                    "failed",
                )
            )

    yield {"event": "tool_calls", "data": [item.model_dump() for item in tool_calls]}
    # With no selected tool, make a second model call so its direct response can
    # be delivered incrementally instead of returning the completed routing turn.
    response_messages = messages if requested_calls else base_messages
    reply_parts: list[str] = []
    try:
        async for chunk in model.astream(response_messages):
            delta = _content_to_text(chunk.content)
            if delta:
                reply_parts.append(delta)
                yield {"event": "delta", "data": {"text": delta}}
    except Exception:
        yield {"event": "error", "data": {"message": "智能摘要暂时不可用，请稍后重试。"}}
        return

    reply = "".join(reply_parts).strip()
    if not reply:
        yield {"event": "error", "data": {"message": "本次分析未生成可展示的文字结论。"}}
        return
    yield {"event": "done", "data": {"tool_calls": [item.model_dump() for item in tool_calls]}}
