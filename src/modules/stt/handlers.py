"""STT bus handlers."""

from typing import Any

from src.bus.interface import MessageConsumer, MessageProducer
from src.core.bus_topics import BusTopics
from src.modules.stt.downloader import MediaDownloader
from src.modules.stt.providers.base import SttProvider
from src.modules.stt.schemas.events import TranscribeCommand
from src.modules.stt.service import SttService


def register_handlers(
    consumer: MessageConsumer,
    producer: MessageProducer,
    downloader: MediaDownloader,
    provider: SttProvider | None = None,
) -> None:
    from src.modules.stt.dependencies import get_stt_provider

    service = SttService(producer, provider or get_stt_provider(), downloader)

    @consumer.subscribe(BusTopics.STT_TRANSCRIBE)
    async def handle_transcribe(message: dict[str, Any]) -> None:
        await service.transcribe(TranscribeCommand.model_validate(message))
