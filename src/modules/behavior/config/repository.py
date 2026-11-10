from src.base.configuration.repository import BaseConfigRepository

from .model import BehaviorConfigModel


class BehaviorConfigRepository(BaseConfigRepository[BehaviorConfigModel]):
    def __init__(self) -> None:
        super().__init__(BehaviorConfigModel)
