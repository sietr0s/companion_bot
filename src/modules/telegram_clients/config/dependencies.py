from .service import TelegramClientsConfigService


def get_configuration_service() -> TelegramClientsConfigService:
    return TelegramClientsConfigService()
