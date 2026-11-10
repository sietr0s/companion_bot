from .service import InstagramClientsConfigService


def get_configuration_service() -> InstagramClientsConfigService:
    return InstagramClientsConfigService()
