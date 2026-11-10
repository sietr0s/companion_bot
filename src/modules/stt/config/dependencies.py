from .service import SttConfigService


def get_configuration_service() -> SttConfigService:
    return SttConfigService()
