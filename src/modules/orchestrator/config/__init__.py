from src.base.configuration.binding import ConfigBinding

from .schema import OrchestratorConfiguration

binding: ConfigBinding[OrchestratorConfiguration, OrchestratorConfiguration] = ConfigBinding(
    OrchestratorConfiguration
)


def get_settings() -> OrchestratorConfiguration:
    return binding.get()


__all__ = ["OrchestratorConfiguration", "binding", "get_settings"]
