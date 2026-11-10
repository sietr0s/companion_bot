from src.base.configuration.service import BaseConfigService

from .model import InstagramClientsConfigModel
from .repository import InstagramClientsConfigRepository
from .schema import InstagramClientsSettings


class InstagramClientsConfigService(
    BaseConfigService[InstagramClientsSettings, InstagramClientsConfigModel]
):
    def __init__(self) -> None:
        super().__init__(InstagramClientsSettings, InstagramClientsConfigRepository())
