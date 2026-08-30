"""LLM module dependency injection factories."""

from src.bus.interface import MessageProducer
from src.modules.llm.service import LLMService


async def get_llm_service(message_bus: MessageProducer) -> LLMService:
    """Get LLM service instance."""
    return LLMService(message_bus=message_bus)
