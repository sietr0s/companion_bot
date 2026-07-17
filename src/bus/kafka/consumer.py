"""
Kafka-реализация консьюмера шины сообщений.

Подписывается на топики Kafka и вызывает зарегистрированные
обработчики при получении сообщений.
При старте ждёт готовности Kafka с экспоненциальным backoff.

Ошибки в обработчиках обрабатываются через BusErrorHandler:
- Бизнес-исключения (AppException) — публикуются в DLQ
- Сетевые ошибки — логируются и публикуются в DLQ
- Неожиданные ошибки — логируются с traceback
"""

import asyncio
import contextlib
import json
import logging
from collections.abc import Callable

import backoff
from aiokafka import AIOKafkaConsumer

from src.bus.error_handler import safe_handle
from src.core.config import settings

logger = logging.getLogger(__name__)


class KafkaConsumerRouter:
    """
    Kafka-консьюмер: слушает топики и вызывает обработчики.

    Получает реестр подписчиков от продюсера и подписывается
    на соответствующие топики Kafka.

    При ошибках подключения выполняет exponential backoff
    с лимитом retry (MAX_RETRIES), после чего завершает работу
    для возможности перезапуска контейнера.
    """

    MAX_RETRIES = 10

    def __init__(self, subscribers: dict[str, list[Callable]]) -> None:
        self._subscribers = subscribers
        self._consumer: AIOKafkaConsumer | None = None
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Запуск консьюмера: подписка на топики и запуск цикла чтения."""
        topics = list(self._subscribers.keys())
        if not topics:
            logger.info("Нет топиков для подписки, KafkaConsumerRouter не запускается")
            return

        @backoff.on_exception(
            backoff.expo,
            Exception,
            max_time=60,
            on_backoff=lambda details: logger.warning(
                "Kafka недоступен для консьюмера (попытка %d): %s. Повтор через %.1fс...",
                details["tries"],
                details["exception"],
                details["wait"],
            ),
        )
        async def _connect() -> None:
            nonlocal_consumer = AIOKafkaConsumer(
                *topics,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id=settings.KAFKA_GROUP_ID,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            )
            await nonlocal_consumer.start()
            self._consumer = nonlocal_consumer

        await _connect()
        # Запускаем цикл чтения с retry в фоновой задаче
        self._task = asyncio.create_task(self._run_with_retry())
        logger.info("KafkaConsumerRouter запущен, топики: %s", topics)

    async def _run_with_retry(self) -> None:
        """Цикл чтения с exponential backoff при ошибках подключения к Kafka."""
        retry_delay = 1
        max_delay = 60
        retries = 0
        while retries < self.MAX_RETRIES:
            try:
                await self._consume()
            except asyncio.CancelledError:
                logger.info("KafkaConsumerRouter: задача отменена, останавливаем retry")
                raise
            except Exception:
                retries += 1
                remaining = self.MAX_RETRIES - retries
                logger.exception(
                    "KafkaConsumerRouter: ошибка (попытка %d/%d), "
                    "перезапуск через %ds, осталось %d попыток",
                    retries,
                    self.MAX_RETRIES,
                    retry_delay,
                    remaining,
                )
                if retries >= self.MAX_RETRIES:
                    logger.critical(
                        "KafkaConsumerRouter: исчерпаны все %d попыток. "
                        "Завершаем работу для перезапуска контейнера.",
                        self.MAX_RETRIES,
                    )
                    return
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_delay)

    async def _consume(self) -> None:
        """Цикл чтения сообщений из Kafka и вызова обработчиков через safe_handle."""
        if not self._consumer:
            return

        try:
            async for msg in self._consumer:
                topic = msg.topic
                handlers = self._subscribers.get(topic, [])
                for handler in handlers:
                    await safe_handle(handler, topic, msg.value)
        except asyncio.CancelledError:
            logger.info("KafkaConsumerRouter: задача чтения отменена")
            raise
        except (ConnectionError, TimeoutError) as e:
            logger.error("Ошибка подключения к Kafka: %s", e)
            raise
        except Exception as e:
            logger.exception("KafkaConsumerRouter: ошибка в цикле чтения: %s", e)
            raise

    async def stop(self) -> None:
        """Остановка консьюмера и фоновой задачи."""
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        if self._consumer:
            await self._consumer.stop()
            logger.info("KafkaConsumerRouter остановлен")
