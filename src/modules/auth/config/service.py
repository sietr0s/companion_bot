from src.base.configuration.service import BaseConfigService

from .model import AuthConfigModel
from .repository import AuthConfigRepository
from .schema import AuthConfiguration


class AuthConfigService(BaseConfigService[AuthConfiguration, AuthConfigModel]):
    def __init__(self) -> None:
        super().__init__(AuthConfiguration, AuthConfigRepository())
