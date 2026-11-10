from src.modules.batching.config.service import BatchingConfigService


def get_configuration_service() -> BatchingConfigService:
    return BatchingConfigService()
