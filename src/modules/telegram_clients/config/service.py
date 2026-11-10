from src.base.configuration.service import BaseConfigService

from .model import TelegramClientsConfigModel
from .repository import TelegramClientsConfigRepository
from .schema import TelegramConfiguration


class TelegramClientsConfigService(
    BaseConfigService[TelegramConfiguration, TelegramClientsConfigModel]
):
    def __init__(self) -> None:
        super().__init__(TelegramConfiguration, TelegramClientsConfigRepository())
