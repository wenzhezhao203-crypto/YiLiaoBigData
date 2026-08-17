"""Application configuration loaded from the project .env file."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


class Config:
    """Runtime configuration for the Flask API."""

    MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "medical_platform")
    MYSQL_USER = os.getenv("MYSQL_USER", "medical_app")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "123456")
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/"
        f"{MYSQL_DATABASE}?charset=utf8mb4"
    )
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
    JSON_AS_ASCII = False
