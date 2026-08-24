"""Embedder adapter (US-18). fastembed instead of sentence-transformers: same
all-MiniLM-L6-v2 model, ONNX runtime instead of PyTorch, roughly a tenth the
install size. Swapping to OpenAI later only touches this file and the
migration's vector(N) width — everything else reads settings.embedding_dim.
"""

from typing import TYPE_CHECKING

from app.adapters.base import Embedder
from app.core.config import settings

if TYPE_CHECKING:
    from fastembed import TextEmbedding

_model: "TextEmbedding | None" = None


def _get_model() -> "TextEmbedding":
    # Lazy module-level singleton: loaded once per worker process, not once
    # per FastEmbedEmbedder() instantiation.
    global _model
    if _model is None:
        from fastembed import TextEmbedding

        _model = TextEmbedding(
            model_name=settings.embedding_model, cache_dir=settings.embedding_cache_dir
        )
    return _model


class FastEmbedEmbedder:
    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = [vector.tolist() for vector in _get_model().embed(texts)]
        for vector in vectors:
            if len(vector) != settings.embedding_dim:
                raise ValueError(
                    f"embedder produced a {len(vector)}-dim vector, "
                    f"expected EMBEDDING_DIM={settings.embedding_dim}"
                )
        return vectors


def get_embedder() -> Embedder:
    if settings.embedder == "fastembed":
        return FastEmbedEmbedder()
    # TS-07 deliberately kept scoring on fastembed only — free, deterministic,
    # offline, already tested; an OpenAI embedder needs a migration (384 -> 1536
    # dims) and a full corpus re-embed for no ranking benefit (drift.md).
    raise NotImplementedError(
        f"embedder={settings.embedder!r} is not implemented; only EMBEDDER=fastembed is supported"
    )
