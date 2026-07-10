"""
Провайдеры шины сообщений.

Отдельный модуль для инициализации шины — без циклических
зависимостей. Используется в dependencies.py и main.py.
"""

from src.bus.interface import MessageBus
from src.core.config import settings


def get_message_bus() -> MessageBus:
    """
    Провайдер шины сообщений.

    Создаёт экземпляр продюсера на основе конфигурации.
    """
    if settings.MESSAGE_BUS == "kafka":
        from src.bus.kafka.producer import KafkaProducerBus

        return KafkaProducerBus()
    from src.bus.in_memory.producer import InMemoryProducer

    return InMemoryProducer()
