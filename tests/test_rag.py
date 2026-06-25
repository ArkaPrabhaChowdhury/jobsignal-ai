from __future__ import annotations

from datetime import UTC, datetime

from src.models import JobListing
from src.rag import RagService


class StubDatabase:
    def similarity_search(self, embedding, limit: int = 15):
        del embedding, limit
        return [
            JobListing(
                id="1",
                title="AI Engineer",
                company="Acme",
                url="https://example.com/1",
                description="LLM systems",
                location="Remote",
                source="indeed",
                skills=["Python", "FastAPI"],
                confidence=0.9,
                embedding=[0.1, 0.2],
                ingested_at=datetime.now(UTC),
            ),
            JobListing(
                id="2",
                title="ML Engineer",
                company="Beta",
                url="https://example.com/2",
                description="Kubernetes pipelines",
                location="Remote",
                source="ddg",
                skills=["Docker", "Kubernetes"],
                confidence=0.8,
                embedding=[0.1, 0.2],
                ingested_at=datetime.now(UTC),
            ),
        ]


class StubEmbedder:
    def embed_text(self, text: str):
        del text
        return [0.1, 0.2]


class StubEnricher:
    def answer_question(self, question: str, context: str):
        return f"Q={question}; C={context}"


def test_rag_query_returns_answer_and_sources():
    service = RagService(
        database=StubDatabase(),
        embedder=StubEmbedder(),
        enricher=StubEnricher(),
    )

    answer, sources = service.query("What skills are trending?")

    assert "What skills are trending?" in answer
    assert sources == ["https://example.com/1", "https://example.com/2"]
