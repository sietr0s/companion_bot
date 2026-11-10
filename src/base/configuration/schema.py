"""Environment-backed schemas for immutable module configuration."""

from pydantic_settings import SettingsConfigDict

from src.core.settings import EnvironmentSettings


class BaseModuleConfig(EnvironmentSettings):
    """Environment-backed, immutable runtime snapshot; DB merging is external."""

    model_config = SettingsConfigDict(frozen=True, allow_inf_nan=False)
