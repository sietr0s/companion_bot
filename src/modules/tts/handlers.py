from typing import Any

from src.bus.interface import MessageConsumer, MessageProducer
from src.core.bus_topics import BusTopics
from src.modules.tts.dependencies import get_tts_provider
from src.modules.tts.schemas.events import SynthesizeCommand
from src.modules.tts.service import TtsService


def register_handlers(consumer: MessageConsumer, producer: MessageProducer) -> None:
    service = TtsService(producer, get_tts_provider())

    @consumer.subscribe(BusTopics.TTS_SYNTHESIZE)
    async def handle_synthesize(message: dict[str, Any]) -> None:
        await service.synthesize(SynthesizeCommand.model_validate(message))
