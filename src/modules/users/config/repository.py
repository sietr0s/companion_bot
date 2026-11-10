from src.base.configuration.repository import BaseConfigRepository

from .model import UsersConfigModel


class UsersConfigRepository(BaseConfigRepository[UsersConfigModel]):
    def __init__(self) -> None:
        super().__init__(UsersConfigModel)
