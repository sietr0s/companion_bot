from src.base.configuration.service import BaseConfigService

from .model import BehaviorConfigModel
from .repository import BehaviorConfigRepository
from .schema import BehaviorSettings


class BehaviorConfigService(BaseConfigService[BehaviorSettings, BehaviorConfigModel]):
    def __init__(self) -> None:
        super().__init__(BehaviorSettings, BehaviorConfigRepository())
