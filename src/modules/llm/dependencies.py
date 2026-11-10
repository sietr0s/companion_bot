"""LLM module dependency injection factories."""

import asyncio
import logging

from src.bus import get_producer
from src.bus.interface import MessageProducer
from src.core.langsmith import configure_langsmith
from src.core.model_cache import apply_model_cache
from src.core.runtime import require_external_services
from src.domain.ai import ChatProvider
from src.modules.llm.config import get_settings
from src.modules.llm.embedder import Embedder, QwenEmbedder
from src.modules.llm.providers.stub import StubChat
from src.modules.llm.service import LLMService

logger = logging.getLogger(__name__)

_embedder: Embedder | None = None
_chat: ChatProvider | None = None


def get_embedder() -> Embedder:
    require_external_services()
    global _embedder
    if _embedder is None:
        _embedder = QwenEmbedder()
    return _embedder


def get_chat_provider() -> ChatProvider:
    require_external_services()
    global _chat
    if _chat is None:
        _chat = build_chat_provider()
    return _chat


def build_chat_provider() -> ChatProvider:
    require_external_services()
    provider = get_settings().LLM_PROVIDER
    if provider == "stub":
        return StubChat()
    if provider == "mistral":
        if not get_settings().MISTRAL_API_KEY:
            raise RuntimeError("LLM_PROVIDER=mistral требует MISTRAL_API_KEY")
        from src.modules.llm.providers.mistral import MistralChat

        return MistralChat(
            api_key=get_settings().MISTRAL_API_KEY,
            model=get_settings().MISTRAL_MODEL,
            presets=get_settings().presets(),
        )
    if provider == "google":
        from src.modules.llm.providers.google import GeminiChat

        return GeminiChat(
            api_key=get_settings().GOOGLE_API_KEY,
            model=get_settings().GOOGLE_MODEL,
            presets=get_settings().presets(),
        )
    if provider in {"openrouter", "openai", "openai_compat"}:
        from src.modules.llm.providers.openai_compat import (
            OPENAI_BASE_URL,
            OPENROUTER_BASE_URL,
            OpenAICompatChat,
        )

        if not get_settings().LLM_API_KEY:
            raise RuntimeError(f"LLM_PROVIDER={provider} требует LLM_API_KEY")
        base_url = get_settings().LLM_BASE_URL
        if not base_url:
            if provider == "openrouter":
                base_url = OPENROUTER_BASE_URL
            elif provider == "openai":
                base_url = OPENAI_BASE_URL
            else:
                raise ValueError("LLM_BASE_URL обязателен для LLM_PROVIDER=openai_compat")
        return OpenAICompatChat(
            api_key=get_settings().LLM_API_KEY,
            model=get_settings().LLM_MODEL,
            base_url=base_url,
            presets=get_settings().presets(),
        )
    raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")


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


def build_llm_service(message_bus: MessageProducer | None = None) -> LLMService:
    return LLMService(
        message_bus=message_bus or get_producer(),
        embedder=get_embedder(),
        chat=get_chat_provider(),
    )


def get_llm_service() -> LLMService:
    return build_llm_service()


def reset_providers() -> None:
    global _embedder, _chat
    _embedder = None
    _chat = None
