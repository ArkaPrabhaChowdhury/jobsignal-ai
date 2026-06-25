from __future__ import annotations

import math

from src.embedder import Embedder


class FakeEmbeddings:
    def __init__(self, rows):
        self.rows = rows

    def tolist(self):
        return self.rows


class FakeModel:
    def __init__(self):
        self.calls = []

    def encode(self, texts, **kwargs):
        self.calls.append((texts, kwargs))
        vector = [1 / math.sqrt(384)] * 384
        return FakeEmbeddings([vector for _ in texts])


def test_embedder_uses_normalized_sentence_transformer_vectors():
    model = FakeModel()
    embedder = Embedder(model=model)

    vectors = embedder.embed_texts(["Go backend engineer", "Golang API developer"])

    assert len(vectors) == 2
    assert len(vectors[0]) == 384
    assert math.isclose(sum(value * value for value in vectors[0]), 1.0)
    assert model.calls[0][1]["normalize_embeddings"] is True
    assert model.calls[0][1]["convert_to_numpy"] is True
