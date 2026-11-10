from src.base.configuration.repository import BaseConfigRepository

from .model import SttConfigModel


class SttConfigRepository(BaseConfigRepository[SttConfigModel]):
    def __init__(self) -> None:
        super().__init__(SttConfigModel)
