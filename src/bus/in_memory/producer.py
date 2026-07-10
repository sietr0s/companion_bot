"""
In-memory реализация продюсера шины сообщений.

Используется в монолитном режиме: обработчики вызываются
синхронно в том же процессе. Это упрощает разработку
и отладку, не требуя внешнего брокера сообщений.
"""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class InMemoryProducer:
    """
    In-memory продюсер: вызывает обработчики напрямую.

    Сохраняет реестр подписчиков, который разделяется
    с InMemoryConsumer для консистентности.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)

    async def publish(self, topic: str, message: dict[str, Any]) -> None:
        """
        Вызывает все обработчики, подписанные на топик.

        Если запущен event loop — асинхронные обработчики
        планируются через create_task. Иначе — вызываются напрямую.
        """
        handlers = self._subscribers.get(topic, [])
        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(handler(message))
                except RuntimeError:
                    # Нет запущенного event loop — вызываем синхронно
                    logger.warning(
                        "Нет запущенного event loop для асинхронного обработчика %s",
                        handler.__name__,
                    )
            else:
                handler(message)

    def subscribe(self, topic: str) -> Callable:
        """
        Декоратор для регистрации обработчика на топик.

        Использование:
            @producer.subscribe(BusTopics.USER_REGISTERED)
            async def handle_user_registered(message):
                ...
        """

        def decorator(func: Callable) -> Callable:
            self._subscribers[topic].append(func)
            logger.info("Зарегистрирован обработчик %s на топик '%s'", func.__name__, topic)
            return func

        return decorator

    def get_subscribers(self) -> dict[str, list[Callable]]:
        """Возвращает копию реестра подписчиков."""
        return dict(self._subscribers)

    async def start(self) -> None:
        """In-memory шина не требует запуска — заглушка."""
        pass

    async def stop(self) -> None:
        """In-memory шина не требует остановки — заглушка."""
        pass
