from src.base.configuration.repository import BaseConfigRepository

from .model import OrchestratorConfigModel


class OrchestratorConfigRepository(BaseConfigRepository[OrchestratorConfigModel]):
    def __init__(self) -> None:
        super().__init__(OrchestratorConfigModel)
