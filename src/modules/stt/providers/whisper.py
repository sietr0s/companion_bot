"""Local faster-whisper STT."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.core.model_cache import apply_model_cache
from src.modules.stt.config import get_settings

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


class FasterWhisperStt:
    def __init__(self, model_size: str | None = None, device: str | None = None) -> None:
        self._model = None
        self._model_size = model_size or get_settings().WHISPER_MODEL
        self._device = device or get_settings().WHISPER_DEVICE

    def _get_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            apply_model_cache()
            logger.info("Загрузка Whisper %s device=%s", self._model_size, self._device)
            self._model = WhisperModel(self._model_size, device=self._device)
            logger.info("Whisper готов")
        return self._model

    def preload(self) -> None:
        self._get_model()

    def transcribe(self, path: Path) -> str:
        model = self._get_model()
        segments, _info = model.transcribe(str(path))
        return "".join(seg.text for seg in segments).strip()
