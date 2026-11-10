from src.base.configuration.repository import BaseConfigRepository
from src.modules.batching.config.model import BatchingConfigModel


class BatchingConfigRepository(BaseConfigRepository[BatchingConfigModel]):
    def __init__(self) -> None:
        super().__init__(BatchingConfigModel)
