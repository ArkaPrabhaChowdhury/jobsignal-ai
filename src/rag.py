from __future__ import annotations

from src.database import Database
from src.embedder import get_embedder
from src.enricher import GroqEnricher


class RagService:
    def __init__(
        self,
        database: Database | None = None,
        embedder=None,
        enricher: GroqEnricher | None = None,
    ) -> None:
        self.database = database or Database()
        self.embedder = embedder or get_embedder()
        self.enricher = enricher or GroqEnricher()

    def query(self, question: str) -> tuple[str, list[str]]:
        embedding = self.embedder.embed_text(question)
        listings = self.database.similarity_search(embedding, limit=15)
        context = "\n".join(
            f"- {item.title} at {item.company} ({', '.join(item.skills)})"
            for item in listings
        )
        answer = self.enricher.answer_question(question, context)
        sources = [item.url for item in listings]
        return answer, sources
