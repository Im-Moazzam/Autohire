"""VectorStore adapter (US-18). pgvector only — Pinecone is dropped (drift
row 10); the Protocol stays so the choice is demonstrated without the
integration cost. Pure Python cosine similarity: deterministic and
reproducible (TC-04), no DB round trip needed to score a single pair.
"""

import math

from app.adapters.base import VectorStore


class PgVectorStore:
    def cosine_similarity(self, vector_a: list[float], vector_b: list[float]) -> float:
        if len(vector_a) != len(vector_b):
            raise ValueError(f"vector length mismatch: {len(vector_a)} vs {len(vector_b)}")
        dot = sum(a * b for a, b in zip(vector_a, vector_b, strict=True))
        norm_a = math.sqrt(sum(a * a for a in vector_a))
        norm_b = math.sqrt(sum(b * b for b in vector_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


def get_vector_store() -> VectorStore:
    # Pinecone is dropped (docs/drift.md row 10) — pgvector is the only
    # implementation in every env; the Protocol is what stays swappable.
    return PgVectorStore()
