"""Явный контейнер долгоживущих компонентов приложения."""

from dataclasses import dataclass

from src.bus import configure_bus, create_bus
from src.bus.interface import MessageConsumer, MessageProducer
from src.modules.instagram_clients.adapters.client_manager import InstagramClientManager
from src.modules.instagram_clients.dependencies import (
    build_instagram_account_service,
    configure_instagram_client_manager,
)
from src.modules.instagram_clients.services import InstagramAccountService
from src.modules.telegram_clients.adapters.client_manager import TelegramClientManager
from src.modules.telegram_clients.dependencies import (
    configure_telegram_client_manager,
    get_telegram_client_service_factory,
)
from src.modules.telegram_clients.services import TelegramAccountService


@dataclass(slots=True)
class ApplicationContainer:
    producer: MessageProducer
    consumer: MessageConsumer
    telegram_client_manager: TelegramClientManager
    telegram_service: TelegramAccountService
    instagram_client_manager: InstagramClientManager
    instagram_service: InstagramAccountService

    @classmethod
    def create(cls, message_bus: str | None = None) -> "ApplicationContainer":
        producer, consumer = create_bus(message_bus)
        configure_bus(producer, consumer)
        client_manager = TelegramClientManager()
        configure_telegram_client_manager(client_manager)
        ig_manager = InstagramClientManager()
        configure_instagram_client_manager(ig_manager)
        telegram_service = get_telegram_client_service_factory(
            client_manager=client_manager,
        )
        return cls(
            producer=producer,
            consumer=consumer,
            telegram_client_manager=client_manager,
            telegram_service=telegram_service,
            instagram_client_manager=ig_manager,
            instagram_service=build_instagram_account_service(client_manager=ig_manager),
        )
