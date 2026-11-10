from src.base.configuration.repository import BaseConfigRepository

from .model import TtsConfigModel


class TtsConfigRepository(BaseConfigRepository[TtsConfigModel]):
    def __init__(self) -> None:
        super().__init__(TtsConfigModel)
