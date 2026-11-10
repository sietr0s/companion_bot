from src.base.configuration.binding import ConfigBinding

from .schema import InstagramClientsSettings

binding: ConfigBinding[InstagramClientsSettings, InstagramClientsSettings] = ConfigBinding(
    InstagramClientsSettings
)


def get_settings() -> InstagramClientsSettings:
    return binding.get()


__all__ = ["InstagramClientsSettings", "binding", "get_settings"]
