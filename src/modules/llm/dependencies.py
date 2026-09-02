"""LLM module dependency injection factories."""

import asyncio
import logging

from src.bus import get_producer
from src.core.config import settings
from src.core.langsmith import configure_langsmith
from src.core.model_cache import apply_model_cache
from src.modules.llm.embedder import Embedder, QwenEmbedder
from src.modules.llm.providers.base import ChatProvider
from src.modules.llm.providers.mistral import MistralChat
from src.modules.llm.providers.openai_compat import (
    OPENAI_BASE_URL,
    OPENROUTER_BASE_URL,
    OpenAICompatChat,
)
from src.modules.llm.providers.stub import StubChat
from src.modules.llm.service import LLMService

logger = logging.getLogger(__name__)

_embedder: Embedder | None = None
_chat: ChatProvider | None = None


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = QwenEmbedder()
    return _embedder


def get_chat_provider() -> ChatProvider:
    global _chat
    if _chat is None:
        _chat = build_chat_provider()
    return _chat


def build_chat_provider() -> ChatProvider:
    provider = (settings.LLM_PROVIDER or "mistral").strip().lower()
    if provider == "stub":
        return StubChat()
    if provider == "mistral":
        api_key = (settings.MISTRAL_API_KEY or "").strip()
        if not api_key:
            raise RuntimeError("LLM_PROVIDER=mistral требует MISTRAL_API_KEY")
        return MistralChat(api_key=api_key, model=settings.MISTRAL_MODEL)
    if provider in {"openrouter", "openai", "openai_compat"}:
        api_key = (settings.LLM_API_KEY or "").strip()
        if not api_key:
            raise RuntimeError(f"LLM_PROVIDER={provider} требует LLM_API_KEY")
        base_url = (settings.LLM_BASE_URL or "").strip()
        if not base_url:
            if provider == "openrouter":
                base_url = OPENROUTER_BASE_URL
            elif provider == "openai":
                base_url = OPENAI_BASE_URL
            else:
                raise ValueError("LLM_BASE_URL обязателен для LLM_PROVIDER=openai_compat")
        return OpenAICompatChat(
            api_key=api_key,
            model=settings.LLM_MODEL,
            base_url=base_url,
        )
    raise ValueError(f"Unsupported LLM_PROVIDER: {settings.LLM_PROVIDER}")


async def warmup_heavy_models() -> None:
    """Load local weights (embeddings) at process start, not on first message."""
    logger.info("Прогрев тяжёлых моделей")
    configure_langsmith()
    apply_model_cache()
    embedder = get_embedder()
    preload = getattr(embedder, "preload", None)
    if callable(preload):
        await asyncio.to_thread(preload)
    provider = get_chat_provider()
    logger.info("Чат-провайдер готов: %s", type(provider).__name__)
    logger.info("Прогрев моделей завершён")


def get_llm_service() -> LLMService:
    return LLMService(
        message_bus=get_producer(),
        embedder=get_embedder(),
        chat=get_chat_provider(),
    )
