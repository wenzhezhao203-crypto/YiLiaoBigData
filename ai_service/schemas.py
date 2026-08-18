"""Pydantic request and response models for the Agent API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Natural-language question sent from the dashboard sidebar."""

    message: str = Field(min_length=1, max_length=500)


class ToolCall(BaseModel):
    """A whitelist analysis tool actually called by the service."""

    name: str
    status: Literal["success", "failed"]


class ChatData(BaseModel):
    """Stage-one response payload consumed by the frontend."""

    reply: str
    tool_calls: list[ToolCall]


class ChatResponse(BaseModel):
    """Standard API response envelope."""

    code: int
    message: str
    data: ChatData


class ReportFilters(BaseModel):
    """Dashboard scope copied from the active BI filters."""

    hospital_service_area: str | None = Field(default=None, max_length=100)
    hospital_county: str | None = Field(default=None, max_length=100)
    facility_name: str | None = Field(default=None, max_length=255)


class ReportRequest(BaseModel):
    """Request for a generated Word report."""

    report_type: Literal["comprehensive", "operations", "patient", "disease"] = "comprehensive"
    filters: ReportFilters = Field(default_factory=ReportFilters)
    focus: str | None = Field(default=None, max_length=300)


class ReportData(BaseModel):
    """Report metadata returned before the DOCX download."""

    report_id: str
    title: str
    report_type: str
    download_path: str
    scope: ReportFilters
    executive_summary: str
    tool_calls: list[ToolCall]
    generated_at: str


class ReportResponse(BaseModel):
    """Standard response for report creation."""

    code: int
    message: str
    data: ReportData | None
