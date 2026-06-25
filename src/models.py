from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class JobListing(BaseModel):
    id: str
    title: str
    company: str
    url: str
    description: str
    location: str
    source: str
    posted_at: str | None = None
    skills: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    embedding: list[float] = Field(default_factory=list)
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RunLog(BaseModel):
    run_id: str
    started_at: datetime
    source: str
    fetched: int = 0
    stored: int = 0
    skipped_dedup: int = 0
    skipped_low_confidence: int = 0
    errors: list[str] = Field(default_factory=list)


class IngestRequest(BaseModel):
    role: str
    sources: list[str]


class QueryResponse(BaseModel):
    answer: str
    sources: list[str]


class ListingPreview(BaseModel):
    id: str
    title: str
    company: str
    url: str
    location: str
    source: str
    posted_at: str | None = None
    skills: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    ingested_at: datetime


class StatsResponse(BaseModel):
    total_listings: int
    by_source: dict[str, int]
    top_skills: list[dict[str, int | str]]
    last_5_runs: list[RunLog]
