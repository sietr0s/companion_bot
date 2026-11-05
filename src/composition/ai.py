"""Connect AI ports to their local implementation at the composition boundary."""

from src.domain.ai import ChatProvider, MemoryIntelligence


def get_memory_intelligence() -> MemoryIntelligence:
    from src.modules.llm.dependencies import get_llm_service

    return get_llm_service()


def get_chat_provider() -> ChatProvider:
    from src.modules.llm.dependencies import get_chat_provider as build

    return build()
