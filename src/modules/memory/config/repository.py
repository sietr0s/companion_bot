from src.base.configuration.repository import BaseConfigRepository

from .model import MemoryConfigModel


class MemoryConfigRepository(BaseConfigRepository[MemoryConfigModel]):
    def __init__(self) -> None:
        super().__init__(MemoryConfigModel)
