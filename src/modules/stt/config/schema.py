from typing import Literal

from src.base.configuration.schema import BaseModuleConfig


class SttConfiguration(BaseModuleConfig):
    STT_PROVIDER: Literal["stub", "whisper", "faster_whisper"] = "faster_whisper"
    WHISPER_MODEL: str = "base"
    WHISPER_DEVICE: str = "cpu"
