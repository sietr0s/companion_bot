from .service import TtsConfigService


def get_configuration_service() -> TtsConfigService:
    return TtsConfigService()
