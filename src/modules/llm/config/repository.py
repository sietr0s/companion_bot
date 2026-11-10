from src.base.configuration.repository import BaseConfigRepository

from .model import LlmConfigModel


class LlmConfigRepository(BaseConfigRepository[LlmConfigModel]):
    def __init__(self) -> None:
        super().__init__(LlmConfigModel)
