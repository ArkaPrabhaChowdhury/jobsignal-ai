from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class Settings(BaseModel):
    groq_api_key: str = Field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    public_ingest_enabled: bool = Field(
        default_factory=lambda: os.getenv("PUBLIC_INGEST_ENABLED", "true").lower() == "true"
    )
    strict_startup: bool = Field(
        default_factory=lambda: os.getenv("STRICT_STARTUP", "false").lower() == "true"
    )
    database_url: str = Field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", "postgresql://user:pass@localhost:5432/cipdb"
        )
    )
    db_connect_timeout_seconds: int = Field(
        default_factory=lambda: int(os.getenv("DB_CONNECT_TIMEOUT_SECONDS", "10"))
    )
    db_startup_retries: int = Field(
        default_factory=lambda: int(os.getenv("DB_STARTUP_RETRIES", "15"))
    )
    db_startup_delay_seconds: float = Field(
        default_factory=lambda: float(os.getenv("DB_STARTUP_DELAY_SECONDS", "2"))
    )
    min_confidence: float = Field(
        default_factory=lambda: float(os.getenv("MIN_CONFIDENCE", "0.6"))
    )
    max_pages: int = Field(default_factory=lambda: int(os.getenv("MAX_PAGES", "3")))
    crawl_delay_ms: int = Field(
        default_factory=lambda: int(os.getenv("CRAWL_DELAY_MS", "1500"))
    )
    raw_save: bool = Field(
        default_factory=lambda: os.getenv("RAW_SAVE", "false").lower() == "true"
    )
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    embedding_model: str = Field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    )
    run_log_db: str = Field(default_factory=lambda: os.getenv("RUN_LOG_DB", "run_logs.db"))
    app_host: str = Field(default_factory=lambda: os.getenv("APP_HOST", "0.0.0.0"))
    port: int = Field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    groq_model: str = "llama-3.1-8b-instant"
    groq_rpm_limit: int = 25
    embedding_dimensions: int = 384


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
