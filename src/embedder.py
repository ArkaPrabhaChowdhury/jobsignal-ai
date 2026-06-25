from __future__ import annotations

from functools import lru_cache
from typing import Any

from src.config import get_settings


class Embedder:
    def __init__(self, model: Any | None = None) -> None:
        self._settings = get_settings()
        self._model = model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        vectors = embeddings.tolist()
        for vector in vectors:
            if len(vector) != self._settings.embedding_dimensions:
                raise ValueError(
                    f"Embedding model produced {len(vector)} dimensions; "
                    f"expected {self._settings.embedding_dimensions}"
                )
        return vectors

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(
                self._settings.embedding_model,
                device="cpu",
            )
            dimensions = self._model.get_sentence_embedding_dimension()
            if dimensions != self._settings.embedding_dimensions:
                raise ValueError(
                    f"{self._settings.embedding_model} produces {dimensions} dimensions; "
                    f"database expects {self._settings.embedding_dimensions}"
                )
        return self._model


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    return Embedder()
