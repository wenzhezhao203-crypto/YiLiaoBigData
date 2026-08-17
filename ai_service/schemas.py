"""Pydantic request and response models for the Agent API."""

from __future__ import annotations

from typing import Literal

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
