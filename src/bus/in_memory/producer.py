"""In-memory producer: только публикует сообщения в транспорт."""

from typing import Any

from src.bus.in_memory.transport import InMemoryMessage, InMemoryTransport
from src.bus.trace import log_published


class InMemoryProducer:
    def __init__(self, transport: InMemoryTransport | None = None) -> None:
        self._transport = transport or InMemoryTransport()

    @property
    def transport(self) -> InMemoryTransport:
        """Транспорт нужен для явной сборки пары в тестах и приложении."""
        return self._transport

    async def publish(self, topic: str, message: dict[str, Any]) -> None:
        log_published(topic, message)
        await self._transport.queue.put(InMemoryMessage(topic, message))

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass
