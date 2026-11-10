"""Instagram clients module settings."""

from pydantic import Field

from src.base.configuration.schema import BaseModuleConfig


class InstagramClientsSettings(BaseModuleConfig):
    INSTAGRAM_POLL_INTERVAL_S: float = Field(default=20, gt=0)
    INSTAGRAM_SESSION_DIR: str = "sessions/instagram"
