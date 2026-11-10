from .service import LlmConfigService


def get_configuration_service() -> LlmConfigService:
    return LlmConfigService()
