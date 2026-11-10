from src.base.configuration.binding import ConfigBinding

from .schema import MemoryConfiguration

binding: ConfigBinding[MemoryConfiguration, MemoryConfiguration] = ConfigBinding(
    MemoryConfiguration
)


def get_settings() -> MemoryConfiguration:
    return binding.get()


__all__ = ["MemoryConfiguration", "binding", "get_settings"]
