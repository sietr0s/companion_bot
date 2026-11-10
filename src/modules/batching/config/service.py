from src.base.configuration.service import BaseConfigService
from src.modules.batching.config.model import BatchingConfigModel
from src.modules.batching.config.repository import BatchingConfigRepository
from src.modules.batching.config.schema import BatchingSettings


class BatchingConfigService(BaseConfigService[BatchingSettings, BatchingConfigModel]):
    def __init__(self) -> None:
        super().__init__(BatchingSettings, BatchingConfigRepository())
