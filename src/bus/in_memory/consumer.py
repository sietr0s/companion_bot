"""In-memory consumer: владеет подписками и обрабатывает очередь."""

import asyncio
import contextlib
import logging
from collections import defaultdict
from collections.abc import Callable

from pydantic import BaseModel, ValidationError

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
        # Храним подписки как dict[topic, list[(action, schema, handler)]]
        self._subscribers: dict[str, list[tuple[str, type[BaseModel], Callable]]] = defaultdict(list)
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._task: asyncio.Task[None] | None = None

    def subscribe(
        self,
        topic: str,
        action: str,
        schema: type[BaseModel],
        handler: Callable[[BaseModel], BaseModel],
    ) -> None:
        """Регистрирует обработчик с типизированной схемой."""
        self._subscribers[topic].append((action, schema, handler))
        logger.info(
            "Зарегистрирован обработчик %s на топик '%s' (action=%s, schema=%s)",
            handler.__name__,
            topic,
            action,
            schema.__name__,
        )

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
            *(self._run_handler(action, schema, handler, envelope) for action, schema, handler in handlers),
            return_exceptions=True,
        )

    async def _run_handler(
        self,
        action: str,
        schema: type[BaseModel],
        handler: Callable[[BaseModel], BaseModel],
        envelope: InMemoryMessage,
    ) -> None:
        async with self._semaphore:
            # Извлекаем payload по action
            payload = envelope.payload.get(action)
            if payload is None:
                logger.warning(
                    "Действие '%s' не найдено в сообщении топика '%s'",
                    action,
                    envelope.topic,
                )
                return

            try:
                # Валидируем входные данные через Pydantic схему
                typed_input = schema.model_validate(payload)
            except ValidationError as e:
                logger.error(
                    "Ошибка валидации схемы %s для действия '%s' в топике '%s': %s",
                    schema.__name__,
                    action,
                    envelope.topic,
                    e,
                )
                return

            # Вызываем обработчик с типизированным объектом
            try:
                typed_output = await handler(typed_input) if asyncio.iscoroutinefunction(handler) else handler(typed_input)

                # Если обработчик вернул событие, публикуем его
                if typed_output is not None and isinstance(typed_output, BaseModel):
                    # Сериализуем output в dict для публикации
                    output_dict = typed_output.model_dump(mode="json")
                    # Публикуем событие в шину
                    await self._producer.publish(
                        f"{envelope.topic}.out",
                        {typed_output.event_name: output_dict} if hasattr(typed_output, "event_name") else output_dict,
                    )
            except Exception as e:
                logger.exception(
                    "Ошибка в обработчике %s для действия '%s' в топике '%s': %s",
                    handler.__name__,
                    action,
                    envelope.topic,
                    e,
                )
                raise

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        logger.info("InMemoryConsumer остановлен")
