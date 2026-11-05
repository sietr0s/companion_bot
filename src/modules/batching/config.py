"""Batch accumulation limits."""

from pydantic import Field

from src.core.settings import EnvironmentSettings


class BatchingSettings(EnvironmentSettings):
    BATCH_MAX_SIZE: int = Field(default=20, ge=1)
    BATCH_IDLE_SECONDS: float = Field(default=2.0, gt=0)


batching_settings = BatchingSettings()
