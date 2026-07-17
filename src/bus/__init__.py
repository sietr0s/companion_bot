import logging

from src.core.config import settings

from .in_memory import InMemoryProducer
from .interface import MessageBus
from .kafka.producer import KafkaProducerBus

logger = logging.getLogger(__name__)

_producer: MessageBus | None = None


def get_producer():
    global _producer
    if _producer is None:
        _producer = KafkaProducerBus() if settings.MESSAGE_BUS == "kafka" else InMemoryProducer()
        logger.info("Создан новый экземпляр MessageBus")
        return _producer
    return _producer

