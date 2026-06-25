from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class JobItem:
    title: str = ""
    company: str = ""
    url: str = ""
    description: str = ""
    location: str = ""
    source: str = ""
    posted_at: str | None = None
    id: str = ""
    skills: list[str] = field(default_factory=list)
    confidence: float = 0.0
    embedding: list[float] = field(default_factory=list)
