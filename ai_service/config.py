"""Configuration for the standalone AI Agent service."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    """Read runtime settings without exposing model credentials in source code."""

    flask_api_base_url = os.getenv("FLASK_API_BASE_URL", "http://127.0.0.1:5000/api").rstrip("/")
    request_timeout_seconds = float(os.getenv("AGENT_REQUEST_TIMEOUT_SECONDS", "15"))
    llm_api_key = os.getenv("LLM_API_KEY", "")
    llm_base_url = os.getenv("LLM_BASE_URL", "")
    llm_model = os.getenv("LLM_MODEL", "")


settings = Settings()
