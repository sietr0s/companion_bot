"""LLM module bus event handlers."""

from src.bus.interface import MessageConsumer
from src.modules.llm.schemas_bus import (
    GenerateReplyCommand,
    PostRetrieveCommand,
    PreRetrieveCommand,
    SummarizeCommand,
)
from src.modules.llm.service import LLMService


def register_handlers(consumer: MessageConsumer, service: LLMService) -> None:
    """Register LLM module event handlers."""

    consumer.subscribe(
        topic="llm.in",
        action="generate_reply",
        schema=GenerateReplyCommand,
        handler=service.generate_reply,
    )

    consumer.subscribe(
        topic="llm.in",
        action="summarize",
        schema=SummarizeCommand,
        handler=service.summarize,
    )

    consumer.subscribe(
        topic="llm.in",
        action="pre_retrieve",
        schema=PreRetrieveCommand,
        handler=service.pre_retrieve,
    )

    consumer.subscribe(
        topic="llm.in",
        action="post_retrieve",
        schema=PostRetrieveCommand,
        handler=service.post_retrieve,
    )
