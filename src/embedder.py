from __future__ import annotations

import hashlib
import math
import re
from functools import lru_cache

from src.config import get_settings


class Embedder:
    def __init__(self) -> None:
        self._settings = get_settings()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_hashing(text) for text in texts]

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def _embed_hashing(self, text: str) -> list[float]:
        """Create a lightweight, deterministic normalized vector for free hosting."""
        vector = [0.0] * self._settings.embedding_dimensions
        tokens = re.findall(r"[a-z0-9+#.]{2,}", text.lower())
        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % len(vector)
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[bucket] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            return [value / norm for value in vector]
        return vector


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    return Embedder()
