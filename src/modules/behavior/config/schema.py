"""Behavior policy settings."""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator

from src.base.configuration.schema import BaseModuleConfig


class BehaviorSettings(BaseModuleConfig):
    BEHAVIOR_TIMEZONE: str = "Europe/Moscow"
    BEHAVIOR_SOFTMAX_TEMP: float = Field(default=1.0, gt=0)
    BEHAVIOR_INTAKE_TIMEOUT_S: float = Field(default=60.0, gt=0)

    @field_validator("BEHAVIOR_TIMEZONE")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as error:
            raise ValueError("BEHAVIOR_TIMEZONE must be a valid IANA timezone") from error
        return value
