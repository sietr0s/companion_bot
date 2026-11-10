from src.base.configuration.binding import ConfigBinding

from .schema import TtsConfiguration, TtsSettings

binding: ConfigBinding[TtsConfiguration, TtsSettings] = ConfigBinding(TtsSettings)


def get_settings() -> TtsSettings:
    return binding.get()


__all__ = ["TtsConfiguration", "binding", "get_settings"]
