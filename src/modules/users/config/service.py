from src.base.configuration.service import BaseConfigService

from .model import UsersConfigModel
from .repository import UsersConfigRepository
from .schema import UsersConfiguration


class UsersConfigService(BaseConfigService[UsersConfiguration, UsersConfigModel]):
    def __init__(self) -> None:
        super().__init__(UsersConfiguration, UsersConfigRepository())
