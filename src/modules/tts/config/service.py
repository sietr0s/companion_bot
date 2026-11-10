from src.base.configuration.service import BaseConfigService

from .model import TtsConfigModel
from .repository import TtsConfigRepository
from .schema import TtsConfiguration


class TtsConfigService(BaseConfigService[TtsConfiguration, TtsConfigModel]):
    def __init__(self) -> None:
        super().__init__(TtsConfiguration, TtsConfigRepository())
