from src.base.configuration.binding import ConfigBinding

from .bootstrap import AuthBootstrapSettings
from .schema import AuthConfiguration

binding: ConfigBinding[AuthConfiguration, AuthConfiguration] = ConfigBinding(AuthConfiguration)


def get_settings() -> AuthConfiguration:
    return binding.get()


__all__ = ["AuthConfiguration", "binding", "get_settings", "AuthBootstrapSettings"]
