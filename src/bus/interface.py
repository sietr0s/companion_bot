"""
Интерфейс шины сообщений (MessageBus).

Определяется как Protocol — структурная типизация Python.
Модули зависят от абстракции, а не от конкретной реализации,
что позволяет подменять in-memory на Kafka без изменений в бизнес-логике.
"""

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MessageBus(Protocol):
    """
    Протокол шины сообщений.

    Реализация может быть in-memory (для монолита)
    или на базе Kafka (для микросервисной архитектуры).
    """

    async def publish(self, topic: str, message: dict[str, Any], await_handlers: bool = False) -> None:
        """Опубликовать сообщение в топик."""
        ...

    def subscribe(self, topic: str) -> Callable:
        """Декоратор для подписки обработчика на топик."""
        ...

    def get_subscribers(self) -> dict[str, list[Callable]]:
        """Получить маппинг топиков на списки обработчиков."""
        ...

    async def start(self) -> None:
        """Запуск шины (подключение к брокеру и т.д.)."""
        ...

    async def stop(self) -> None:
        """Остановка шины (закрытие соединений)."""
        ...
