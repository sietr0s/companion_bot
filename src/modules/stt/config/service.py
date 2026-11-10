from src.base.configuration.service import BaseConfigService

from .model import SttConfigModel
from .repository import SttConfigRepository
from .schema import SttConfiguration


class SttConfigService(BaseConfigService[SttConfiguration, SttConfigModel]):
    def __init__(self) -> None:
        super().__init__(SttConfiguration, SttConfigRepository())
