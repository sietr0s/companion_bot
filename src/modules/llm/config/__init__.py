from src.base.configuration.binding import ConfigBinding

from .schema import LLMConfiguration, LLMSettings

binding: ConfigBinding[LLMConfiguration, LLMSettings] = ConfigBinding(LLMSettings)


def get_settings() -> LLMSettings:
    return binding.get()


__all__ = ["LLMConfiguration", "binding", "get_settings", "LLMSettings"]
