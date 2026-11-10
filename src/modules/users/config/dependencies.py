from .service import UsersConfigService


def get_configuration_service() -> UsersConfigService:
    return UsersConfigService()
