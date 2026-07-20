"""Раздельные интерфейсы издателя и потребителя сообщений."""

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MessageProducer(Protocol):
    """Публикует сообщения, но не знает об обработчиках."""

    async def publish(self, topic: str, message: dict[str, Any]) -> None:
        """Опубликовать сообщение в топик."""
        ...

    async def start(self) -> None:
        """Запустить подключение к транспорту."""
        ...

    async def stop(self) -> None:
        """Остановить подключение к транспорту."""
        ...


@runtime_checkable
class MessageConsumer(Protocol):
    """Регистрирует обработчики и получает сообщения из транспорта."""

    def subscribe(self, topic: str) -> Callable:
        """Вернуть декоратор регистрации обработчика топика."""
        ...

    def get_subscribers(self) -> dict[str, list[Callable]]:
        """Вернуть отображение топиков на обработчики."""
        ...

    async def start(self) -> None:
        """Начать получение сообщений."""
        ...

    async def stop(self) -> None:
        """Остановить получение сообщений."""
        ...


# Временный алиас для прикладных сервисов, которым нужна только публикация.
# Новый код должен использовать MessageProducer явно.
MessageBus = MessageProducer
