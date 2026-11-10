from .service import AuthConfigService


def get_configuration_service() -> AuthConfigService:
    return AuthConfigService()
