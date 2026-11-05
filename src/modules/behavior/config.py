"""Behavior policy settings."""

from pydantic import Field

from src.core.settings import EnvironmentSettings


class BehaviorSettings(EnvironmentSettings):
    BEHAVIOR_TIMEZONE: str = "Europe/Moscow"
    BEHAVIOR_SOFTMAX_TEMP: float = Field(default=1.0, gt=0)
    BEHAVIOR_INTAKE_TIMEOUT_S: float = Field(default=60.0, gt=0)


behavior_settings = BehaviorSettings()
