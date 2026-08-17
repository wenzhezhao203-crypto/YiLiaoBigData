"""FastAPI entry point for the AI sidebar Agent service."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from ai_service.agent import answer_question, stream_answer_question
from ai_service.schemas import ChatData, ChatRequest, ChatResponse


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="智慧医疗 AI Agent", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/ai/health")
async def health_check() -> dict[str, object]:
    return {"code": 0, "message": "success", "data": {"status": "ok"}}


@app.post("/ai/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    message = request.message.strip()
    if not message:
        return ChatResponse(
            code=40001,
            message="invalid message",
            data=ChatData(reply="请输入需要分析的问题。", tool_calls=[]),
        )

    logger.info("Processing Agent request with %s characters", len(message))
    data = await answer_question(message)
    failed = any(item.status == "failed" for item in data.tool_calls)
    return ChatResponse(
        code=50001 if failed else 0,
        message="agent request failed" if failed else "success",
        data=data,
    )


@app.post("/ai/chat/stream")
async def stream_chat(request: ChatRequest) -> StreamingResponse:
    """Stream the final LLM reply as Server-Sent Events."""

    message = request.message.strip()

    async def events() -> AsyncIterator[str]:
        if not message:
            payload = {"message": "请输入需要分析的问题。"}
            yield f"event: error\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
            return
        async for item in stream_answer_question(message):
            payload = json.dumps(item["data"], ensure_ascii=False)
            yield f"event: {item['event']}\ndata: {payload}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
