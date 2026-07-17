"""
In-memory реализация продюсера шины сообщений.

Используется в монолитном режиме: обработчики вызываются
синхронно в том же процессе. Это упрощает разработку
и отладку, не требуя внешнего брокера сообщений.

Ошибки в обработчиках обрабатываются через BusErrorHandler:
- Бизнес-исключения (AppException) — публикуются в DLQ
- Сетевые ошибки — логируются и публикуются в DLQ
- Неожиданные ошибки — логируются с traceback
"""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from src.bus.error_handler import safe_handle

logger = logging.getLogger(__name__)


class InMemoryProducer:
    """
    In-memory продюсер: вызывает обработчики напрямую.

    Сохраняет реестр подписчиков, который разделяется
    с InMemoryConsumer для консистентности.

    Ограничивает количество конкурентных задач через Semaphore,
    чтобы избежать перегрузки event loop при пиковых нагрузках.
    """

    def __init__(self, max_concurrent: int = 100) -> None:
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def publish(self, topic: str, message: dict[str, Any], await_handlers: bool = False) -> None:
        """
        Вызывает все обработчики, подписанные на топик.

        Если запущен event loop — асинхронные обработчики
        планируются через create_task с ограничением через Semaphore.
        Иначе — вызываются напрямую.
        Ошибки обрабатываются через safe_handle — бизнес-исключения
        публикуются в DLQ, остальные логируются.

        Если await_handlers=True — дожидается завершения всех
        обработчиков через asyncio.gather с return_exceptions=True.
        """
        handlers = self._subscribers.get(topic, [])
        tasks: list[asyncio.Task] = []
        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                try:
                    loop = asyncio.get_running_loop()
                    task = loop.create_task(
                        self._run_with_semaphore(handler, topic, message)
                    )
                    tasks.append(task)
                except RuntimeError:
                    # Нет запущенного event loop — вызываем напрямую
                    await safe_handle(handler, topic, message)
            else:
                handler(message)

        if await_handlers and tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _run_with_semaphore(
        self, handler: Callable, topic: str, message: dict[str, Any]
    ) -> None:
        """Запустить обработчик под семафором."""
        async with self._semaphore:
            await safe_handle(handler, topic, message)

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
