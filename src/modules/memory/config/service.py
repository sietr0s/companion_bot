from src.base.configuration.service import BaseConfigService

from .model import MemoryConfigModel
from .repository import MemoryConfigRepository
from .schema import MemoryConfiguration


class MemoryConfigService(BaseConfigService[MemoryConfiguration, MemoryConfigModel]):
    def __init__(self) -> None:
        super().__init__(MemoryConfiguration, MemoryConfigRepository())
