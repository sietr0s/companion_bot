from .service import OrchestratorConfigService


def get_configuration_service() -> OrchestratorConfigService:
    return OrchestratorConfigService()
