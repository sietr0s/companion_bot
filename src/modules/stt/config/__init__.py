from src.base.configuration.binding import ConfigBinding

from .schema import SttConfiguration

binding: ConfigBinding[SttConfiguration, SttConfiguration] = ConfigBinding(SttConfiguration)


def get_settings() -> SttConfiguration:
    return binding.get()


__all__ = ["SttConfiguration", "binding", "get_settings"]
