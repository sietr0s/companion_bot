from src.base.configuration.binding import ConfigBinding

from .schema import BehaviorSettings

binding: ConfigBinding[BehaviorSettings, BehaviorSettings] = ConfigBinding(BehaviorSettings)


def get_settings() -> BehaviorSettings:
    return binding.get()


__all__ = ["BehaviorSettings", "binding", "get_settings"]
