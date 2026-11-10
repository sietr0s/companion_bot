from src.base.configuration.repository import BaseConfigRepository

from .model import InstagramClientsConfigModel


class InstagramClientsConfigRepository(BaseConfigRepository[InstagramClientsConfigModel]):
    def __init__(self) -> None:
        super().__init__(InstagramClientsConfigModel)
