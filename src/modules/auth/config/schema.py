from pydantic import Field

from src.base.configuration.schema import BaseModuleConfig


class AuthConfiguration(BaseModuleConfig):
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440, ge=1)
