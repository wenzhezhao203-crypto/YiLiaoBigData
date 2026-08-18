"""FastAPI entry point for the AI sidebar Agent service."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from ai_service.agent import answer_question, stream_answer_question
from ai_service.report_service import generate_report_document
from ai_service.schemas import ChatData, ChatRequest, ChatResponse, ReportData, ReportRequest, ReportResponse


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
REPORT_FILES: dict[str, tuple[Path, float]] = {}
REPORT_TTL_SECONDS = 15 * 60

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


def _cleanup_reports() -> None:
    now = time.time()
    for report_id, (path, expires_at) in list(REPORT_FILES.items()):
        if expires_at < now:
            REPORT_FILES.pop(report_id, None)
            try:
                path.unlink(missing_ok=True)
            except OSError:
                logger.warning("Could not remove expired report %s", report_id)


@app.post("/ai/report", response_model=ReportResponse)
async def create_report(request: ReportRequest) -> ReportResponse:
    """Generate a short-lived Word report from approved dashboard summaries."""

    _cleanup_reports()
    try:
        report_id, path, report, tool_calls = await generate_report_document(request)
    except Exception as error:
        logger.exception("Report generation failed: %s", error)
        return ReportResponse(code=50002, message="report generation failed", data=None)
    REPORT_FILES[report_id] = (path, time.time() + REPORT_TTL_SECONDS)
    data = ReportData(
        report_id=report_id,
        title=report["title"],
        report_type=request.report_type,
        download_path=f"/ai/report/{report_id}/download",
        scope=request.filters,
        executive_summary=report["executive_summary"],
        tool_calls=tool_calls,
        generated_at=report["generated_at"],
    )
    return ReportResponse(code=0, message="success", data=data)


@app.get("/ai/report/{report_id}/download")
async def download_report(report_id: str) -> FileResponse:
    """Download a generated report while its temporary link is valid."""

    _cleanup_reports()
    item = REPORT_FILES.get(report_id)
    if not item or not item[0].is_file():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="report not found or expired")
    return FileResponse(
        item[0],
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="medical_analysis_report.docx",
    )
