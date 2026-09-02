"""Сборка producer и consumer для выбранного транспорта."""

import logging

from src.bus.interface import MessageConsumer, MessageProducer

logger = logging.getLogger(__name__)

_producer: MessageProducer | None = None
_consumer: MessageConsumer | None = None


def configure_bus(producer: MessageProducer, consumer: MessageConsumer) -> None:
    """Установить пару шины, которую используют фабрики приложения."""
    global _producer, _consumer
    _producer = producer
    _consumer = consumer


def create_bus(message_bus: str | None = None) -> tuple[MessageProducer, MessageConsumer]:
    """Создать независимую пару producer/consumer."""
    from src.core.config import settings

    transport_name = message_bus or settings.MESSAGE_BUS
    if transport_name == "kafka":
        from src.bus.kafka.consumer import KafkaConsumerRouter
        from src.bus.kafka.producer import KafkaProducerBus

        return KafkaProducerBus(), KafkaConsumerRouter()

    from src.bus.in_memory import InMemoryConsumer, InMemoryProducer, InMemoryTransport

    transport = InMemoryTransport()
    return InMemoryProducer(transport), InMemoryConsumer(transport)


def _ensure_bus() -> None:
    global _producer, _consumer
    if _producer is None or _consumer is None:
        _producer, _consumer = create_bus()
        logger.info("Создана пара producer/consumer")


def get_producer() -> MessageProducer:
    _ensure_bus()
    assert _producer is not None
    return _producer


def get_consumer() -> MessageConsumer:
    _ensure_bus()
    assert _consumer is not None
    return _consumer
