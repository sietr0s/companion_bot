"""LLM module bus event handlers."""

from typing import Any

from src.bus.interface import MessageConsumer, MessageProducer
from src.core.bus_topics import BusTopics
from src.modules.llm.dependencies import get_chat_provider, get_embedder
from src.modules.llm.schemas.events import GenerateReplyCommand, SummarizeCommand
from src.modules.llm.service import LLMService


def register_handlers(consumer: MessageConsumer, producer: MessageProducer) -> None:
    service = LLMService(producer, get_embedder(), get_chat_provider())

    @consumer.subscribe(BusTopics.LLM_GENERATE_REPLY)
    async def handle_generate_reply(message: dict[str, Any]) -> None:
        await service.generate_reply(GenerateReplyCommand.model_validate(message))

    @consumer.subscribe(BusTopics.LLM_SUMMARIZE)
    async def handle_summarize(message: dict[str, Any]) -> None:
        await service.summarize_command(SummarizeCommand.model_validate(message))
