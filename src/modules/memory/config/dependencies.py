from .service import MemoryConfigService


def get_configuration_service() -> MemoryConfigService:
    return MemoryConfigService()
