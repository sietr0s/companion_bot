"""STT DI."""

from __future__ import annotations

import logging

from src.core.config import settings
from src.modules.stt.providers.base import SttProvider
from src.modules.stt.providers.stub import StubStt

logger = logging.getLogger(__name__)

_stt: SttProvider | None = None


def get_stt_provider() -> SttProvider:
    global _stt
    if _stt is None:
        _stt = build_stt_provider()
    return _stt


def build_stt_provider() -> SttProvider:
    name = (settings.STT_PROVIDER or "faster_whisper").strip().lower()
    if name == "stub":
        return StubStt()
    if name in {"faster_whisper", "whisper"}:
        from src.modules.stt.providers.whisper import FasterWhisperStt

        return FasterWhisperStt()
    raise ValueError(f"Unsupported STT_PROVIDER: {settings.STT_PROVIDER}")


async def warmup_stt() -> None:
    provider = get_stt_provider()
    preload = getattr(provider, "preload", None)
    if callable(preload):
        import asyncio

        await asyncio.to_thread(preload)
    logger.info("STT-провайдер готов: %s", type(provider).__name__)
