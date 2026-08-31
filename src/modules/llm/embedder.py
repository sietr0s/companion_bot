"""Local embedding backend (Qwen via sentence-transformers)."""

from __future__ import annotations

from typing import Literal, Protocol

from src.core.config import settings


class Embedder(Protocol):
    def embed(
        self, texts: list[str], *, role: Literal["query", "document"]
    ) -> list[list[float]]: ...


class QwenEmbedder:
    """Lazy-loads SentenceTransformer(settings.EMBEDDING_MODEL) on first embed."""

    def __init__(self) -> None:
        self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(settings.EMBEDDING_MODEL)
        return self._model

    def embed(
        self, texts: list[str], *, role: Literal["query", "document"]
    ) -> list[list[float]]:
        model = self._get_model()
        # Qwen3-Embedding: queries use the built-in "query" prompt; documents are raw.
        if role == "query":
            vectors = model.encode(texts, prompt_name="query")
        else:
            vectors = model.encode(texts)
        return [list(map(float, row)) for row in vectors]
