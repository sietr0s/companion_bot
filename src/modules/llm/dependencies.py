"""LLM module dependency injection factories."""

from src.bus import get_producer
from src.modules.llm.embedder import Embedder, QwenEmbedder
from src.modules.llm.service import LLMService

_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = QwenEmbedder()
    return _embedder


def get_llm_service() -> LLMService:
    return LLMService(message_bus=get_producer(), embedder=get_embedder())
