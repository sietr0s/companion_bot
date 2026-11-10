from src.base.configuration.service import BaseConfigService

from .model import OrchestratorConfigModel
from .repository import OrchestratorConfigRepository
from .schema import OrchestratorConfiguration


class OrchestratorConfigService(
    BaseConfigService[OrchestratorConfiguration, OrchestratorConfigModel]
):
    def __init__(self) -> None:
        super().__init__(OrchestratorConfiguration, OrchestratorConfigRepository())
