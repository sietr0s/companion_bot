"""STT DI."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.core.runtime import require_external_services
from src.modules.stt.config import get_settings
from src.modules.stt.providers.stub import StubStt

if TYPE_CHECKING:
    from src.modules.stt.providers.base import SttProvider

logger = logging.getLogger(__name__)

_stt: SttProvider | None = None


def get_stt_provider() -> SttProvider:
    require_external_services()
    global _stt
    if _stt is None:
        _stt = build_stt_provider()
    return _stt


def build_stt_provider() -> SttProvider:
    require_external_services()
    name = (get_settings().STT_PROVIDER or "faster_whisper").strip().lower()
    if name == "stub":
        return StubStt()
    if name in {"faster_whisper", "whisper"}:
        from src.modules.stt.providers.whisper import FasterWhisperStt

        return FasterWhisperStt()
    raise ValueError(f"Unsupported STT_PROVIDER: {get_settings().STT_PROVIDER}")


async def warmup_stt() -> None:
    provider = get_stt_provider()
    preload = getattr(provider, "preload", None)
    if callable(preload):
        import asyncio

        await asyncio.to_thread(preload)
    logger.info("STT-провайдер готов: %s", type(provider).__name__)


def reset_provider() -> None:
    global _stt
    _stt = None
