"""In-memory реализация шины сообщений."""

from src.bus.in_memory.consumer import InMemoryConsumer
from src.bus.in_memory.producer import InMemoryProducer

__all__ = ["InMemoryConsumer", "InMemoryProducer"]