from typing import Literal

from pydantic import Field

from src.base.configuration.schema import BaseModuleConfig
from src.core.settings import EnvironmentSettings


class TtsConfiguration(BaseModuleConfig):
    TTS_PROVIDER: Literal["stub", "openrouter", "openai", "openai_compat"] = "stub"
    TTS_MODEL: str = "openai/gpt-4o-mini-tts-2025-12-15"
    TTS_VOICE: str = "alloy"
    TTS_RESPONSE_FORMAT: str = "mp3"
    LLM_BASE_URL: str = ""


class TtsBootstrapSettings(EnvironmentSettings):
    LLM_API_KEY: str = Field(default="", repr=False)


class TtsSettings(TtsConfiguration, TtsBootstrapSettings):
    """Module snapshot with ENV-only TTS credentials."""
