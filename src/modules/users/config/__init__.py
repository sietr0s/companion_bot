from src.base.configuration.binding import ConfigBinding

from .schema import UsersConfiguration

binding: ConfigBinding[UsersConfiguration, UsersConfiguration] = ConfigBinding(UsersConfiguration)


def get_settings() -> UsersConfiguration:
    return binding.get()


__all__ = ["UsersConfiguration", "binding", "get_settings"]
