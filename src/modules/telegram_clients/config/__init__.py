from src.base.configuration.binding import ConfigBinding

from .schema import TelegramConfiguration, TelegramRuntimeSettings

binding: ConfigBinding[TelegramConfiguration, TelegramRuntimeSettings] = ConfigBinding(
    TelegramRuntimeSettings
)


def get_settings() -> TelegramRuntimeSettings:
    return binding.get()


__all__ = ["TelegramConfiguration", "binding", "get_settings"]
