"""In-memory consumer: владеет подписками и обрабатывает очередь."""

import asyncio
import contextlib
import logging
from collections import defaultdict
from collections.abc import Callable

from src.bus.error_handler import safe_handle
from src.bus.in_memory.transport import InMemoryMessage, InMemoryTransport
from src.bus.interface import MessageProducer

logger = logging.getLogger(__name__)


class InMemoryConsumer:
    def __init__(
        self,
        transport: InMemoryTransport,
        producer: MessageProducer,
        max_concurrent: int = 100,
    ) -> None:
        self._transport = transport
        self._producer = producer
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._task: asyncio.Task[None] | None = None

    def subscribe(self, topic: str) -> Callable:
        """Зарегистрировать обработчик на топик."""

        def decorator(func: Callable) -> Callable:
            self._subscribers[topic].append(func)
            logger.info(
                "Зарегистрирован обработчик %s на топик '%s'",
                func.__name__,
                topic,
            )
            return func

        return decorator

    def get_subscribers(self) -> dict[str, list[Callable]]:
        return dict(self._subscribers)

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._consume())
            logger.info("InMemoryConsumer запущен")

    async def _consume(self) -> None:
        while True:
            envelope = await self._transport.queue.get()
            try:
                await self._dispatch(envelope)
            finally:
                self._transport.queue.task_done()

    async def _dispatch(self, envelope: InMemoryMessage) -> None:
        handlers = self._subscribers.get(envelope.topic, [])
        if not handlers:
            return

        await asyncio.gather(
            *(self._run_handler(handler, envelope) for handler in handlers),
            return_exceptions=True,
        )

    async def _run_handler(self, handler: Callable, envelope: InMemoryMessage) -> None:
        async with self._semaphore:
            await safe_handle(
                handler,
                envelope.topic,
                envelope.payload,
                self._producer.publish,
            )

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        logger.info("InMemoryConsumer остановлен")
