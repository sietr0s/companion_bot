"""
In-memory реализация консьюмера шины сообщений.

В монолитном режиме консьюмер — это заглушка, так как
все обработчики уже вызываются синхронно через InMemoryProducer.
Нужен для единообразия интерфейса и для будущего перехода на Kafka.
"""

import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)


class InMemoryConsumer:
    """
    In-memory консьюмер: заглушка для монолитного режима.

    В in-memory режиме обработчики вызываются продюсером напрямую,
    поэтому консьюмеру не нужно ничего делать — он просто хранит
    реестр подписчиков для совместимости с интерфейсом.
    """

    def __init__(self, subscribers: dict[str, list[Callable]]) -> None:
        self._subscribers = subscribers

    async def start(self) -> None:
        """В in-memory режиме запуск консьюмера не требуется."""
        logger.info("InMemoryConsumer запущен (режим заглушки)")

    async def stop(self) -> None:
        """В in-memory режиме остановка консьюмера не требуется."""
        logger.info("InMemoryConsumer остановлен")
