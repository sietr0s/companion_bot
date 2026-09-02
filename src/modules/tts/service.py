"""TTS business logic."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

from src.bus.interface import MessageProducer
from src.core.bus_topics import BusTopics
from src.modules.tts.providers.base import TtsProvider
from src.modules.tts.schemas.events import (
    SynthesizeCommand,
    SynthesizeSkippedEvent,
    SynthesizedEvent,
)

logger = logging.getLogger(__name__)


class TtsService:
    def __init__(self, message_bus: MessageProducer, provider: TtsProvider) -> None:
        self._message_bus = message_bus
        self._provider = provider

    async def synthesize(self, command: SynthesizeCommand) -> None:
        try:
            audio = await self._provider.synthesize(command.text)
        except Exception:
            logger.exception("tts failed chat=%s", command.chat_id)
            await self._skip(command, reason="error")
            return
        if not audio:
            await self._skip(command, reason="stub")
            return
        suffix = ".mp3"
        fmt = getattr(self._provider, "_response_format", None)
        if fmt == "pcm":
            suffix = ".pcm"
        fd, name = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        path = Path(name)
        path.write_bytes(audio)
        content_type = getattr(self._provider, "last_content_type", None) or "audio/mpeg"
        generation_id = getattr(self._provider, "last_generation_id", None)
        event = SynthesizedEvent(
            account_id=command.account_id,
            chat_id=command.chat_id,
            path=str(path),
            content_type=content_type,
            generation_id=generation_id,
        )
        await self._message_bus.publish(BusTopics.TTS_SYNTHESIZED, event.to_bus_dict())

    async def _skip(self, command: SynthesizeCommand, *, reason: str) -> None:
        event = SynthesizeSkippedEvent(
            account_id=command.account_id,
            chat_id=command.chat_id,
            reason=reason,
        )
        await self._message_bus.publish(
            BusTopics.TTS_SYNTHESIZE_SKIPPED, event.to_bus_dict()
        )
