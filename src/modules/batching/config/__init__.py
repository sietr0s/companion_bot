from src.base.configuration.binding import ConfigBinding

from .schema import BatchingSettings

binding: ConfigBinding[BatchingSettings, BatchingSettings] = ConfigBinding(BatchingSettings)


def get_settings() -> BatchingSettings:
    return binding.get()


__all__ = ["BatchingSettings", "binding", "get_settings"]
