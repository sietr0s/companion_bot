from src.base.configuration.repository import BaseConfigRepository

from .model import AuthConfigModel


class AuthConfigRepository(BaseConfigRepository[AuthConfigModel]):
    def __init__(self) -> None:
        super().__init__(AuthConfigModel)
