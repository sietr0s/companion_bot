from src.base.configuration.repository import BaseConfigRepository

from .model import TelegramClientsConfigModel


class TelegramClientsConfigRepository(BaseConfigRepository[TelegramClientsConfigModel]):
    def __init__(self) -> None:
        super().__init__(TelegramClientsConfigModel)
