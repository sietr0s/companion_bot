"""STT business logic."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from src.bus.interface import MessageProducer
from src.core.bus_topics import BusTopics
from src.modules.stt.downloader import MediaDownloader
from src.modules.stt.providers.base import SttProvider
from src.modules.stt.schemas.events import (
    TranscribeCommand,
    TranscribeFailedEvent,
    TranscribedEvent,
)

logger = logging.getLogger(__name__)


class SttService:
    def __init__(
        self,
        message_bus: MessageProducer,
        provider: SttProvider,
        downloader: MediaDownloader,
    ) -> None:
        self._message_bus = message_bus
        self._provider = provider
        self._downloader = downloader

    async def transcribe(self, command: TranscribeCommand) -> None:
        path: Path | None = None
        try:
            path = await self._downloader.download_voice(
                command.account_id, command.chat_id, command.message_id
            )
            text = await asyncio.to_thread(self._provider.transcribe, path)
            if not (text or "").strip():
                raise ValueError("empty transcript")
            event = TranscribedEvent(
                account_id=command.account_id,
                chat_id=command.chat_id,
                message_id=command.message_id,
                text=text.strip(),
                media_type=command.media_type,
                reply_to=command.reply_to,
                forward_from=command.forward_from,
            )
            await self._message_bus.publish(BusTopics.STT_TRANSCRIBED, event.to_bus_dict())
        except Exception as exc:
            logger.exception("stt failed chat=%s message=%s", command.chat_id, command.message_id)
            failed = TranscribeFailedEvent(
                account_id=command.account_id,
                chat_id=command.chat_id,
                message_id=command.message_id,
                reason=str(exc),
            )
            await self._message_bus.publish(
                BusTopics.STT_TRANSCRIBE_FAILED, failed.to_bus_dict()
            )
        finally:
            if path is not None:
                path.unlink(missing_ok=True)
