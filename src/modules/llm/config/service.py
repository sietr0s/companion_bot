from src.base.configuration.service import BaseConfigService

from .model import LlmConfigModel
from .repository import LlmConfigRepository
from .schema import LLMConfiguration


class LlmConfigService(BaseConfigService[LLMConfiguration, LlmConfigModel]):
    def __init__(self) -> None:
        super().__init__(LLMConfiguration, LlmConfigRepository())
