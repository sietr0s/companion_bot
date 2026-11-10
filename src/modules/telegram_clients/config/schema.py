from pydantic import Field

from src.base.configuration.schema import BaseModuleConfig
from src.core.settings import EnvironmentSettings


class TelegramConfiguration(BaseModuleConfig):
    TG_SESSION_DIR: str = "sessions"
    TG_APP_VERSION: str = "modular_monolith"
    TG_DEVICE_MODEL: str = "ModularMonolith"
    TG_SYSTEM_VERSION: str = "4.16.30-vxCUSTOM"


class TelegramBootstrapSettings(EnvironmentSettings):
    TG_API_ID: int = 0
    TG_API_HASH: str = Field(default="", repr=False)


class TelegramRuntimeSettings(TelegramConfiguration, TelegramBootstrapSettings):
    """Module snapshot with ENV-only Telegram credentials."""
