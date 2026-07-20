"""Явный контейнер долгоживущих компонентов приложения."""

from dataclasses import dataclass

from src.bus import configure_bus, create_bus
from src.bus.interface import MessageConsumer, MessageProducer
from src.modules.telegram_clients.client_manager import TelegramClientManager
from src.modules.telegram_clients.dependencies import get_telegram_client_service_factory
from src.modules.telegram_clients.services import TelegramAccountService


@dataclass(slots=True)
class ApplicationContainer:
    producer: MessageProducer
    consumer: MessageConsumer
    telegram_client_manager: TelegramClientManager
    telegram_service: TelegramAccountService

    @classmethod
    def create(cls, message_bus: str | None = None) -> "ApplicationContainer":
        producer, consumer = create_bus(message_bus)
        configure_bus(producer, consumer)
        client_manager = TelegramClientManager()
        telegram_service = get_telegram_client_service_factory(
            client_manager=client_manager,
        )
        return cls(
            producer=producer,
            consumer=consumer,
            telegram_client_manager=client_manager,
            telegram_service=telegram_service,
        )
