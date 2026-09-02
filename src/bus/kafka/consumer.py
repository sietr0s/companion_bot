"""
Kafka-реализация консьюмера шины сообщений.

Подписывается на топики Kafka и вызывает зарегистрированные
обработчики при получении сообщений.
При старте ждёт готовности Kafka с экспоненциальным backoff.

Ошибки в обработчиках логируются через safe_handle и не роняют консьюмер.
"""

import asyncio
import contextlib
import json
import logging
from collections import defaultdict
from collections.abc import Callable

import backoff
from aiokafka import AIOKafkaConsumer

from src.bus.error_handler import safe_handle
from src.bus.trace import log_received
from src.core.config import settings

logger = logging.getLogger(__name__)


class KafkaConsumerRouter:
    """
    Kafka-консьюмер: слушает топики и вызывает обработчики.

    Сам владеет реестром подписчиков и подписывается
    на соответствующие топики Kafka.

    При ошибках подключения выполняет exponential backoff
    с лимитом retry (MAX_RETRIES), после чего завершает работу
    для возможности перезапуска контейнера.
    """

    MAX_RETRIES = 10

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._consumer: AIOKafkaConsumer | None = None
        self._task: asyncio.Task | None = None
        self._topics: tuple[str, ...] = ()

    def subscribe(self, topic: str) -> Callable:
        """Зарегистрировать обработчик и топик, который будет читать consumer."""

        def decorator(func: Callable) -> Callable:
            self._subscribers[topic].append(func)
            logger.info("Зарегистрирован обработчик %s на топик '%s'", func.__name__, topic)
            return func

        return decorator

    def get_subscribers(self) -> dict[str, list[Callable]]:
        return dict(self._subscribers)

    async def start(self) -> None:
        """Запуск консьюмера: подписка на топики и запуск цикла чтения."""
        self._topics = tuple(self._subscribers)
        if not self._topics:
            logger.info("Нет топиков для подписки, KafkaConsumerRouter не запускается")
            return

        await self._connect_with_backoff()
        # Запускаем цикл чтения с retry в фоновой задаче
        self._task = asyncio.create_task(self._run_with_retry())
        logger.info("KafkaConsumerRouter запущен, топики: %s", self._topics)

    async def _connect(self) -> None:
        """Создать новый consumer и атомарно заменить им прежний."""
        consumer = AIOKafkaConsumer(
            *self._topics,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_GROUP_ID,
            value_deserializer=lambda message: json.loads(message.decode("utf-8")),
        )
        try:
            await consumer.start()
        except Exception:
            with contextlib.suppress(Exception):
                await consumer.stop()
            raise
        self._consumer = consumer

    @backoff.on_exception(backoff.expo, Exception, max_time=60)
    async def _connect_with_backoff(self) -> None:
        """Подключиться при старте с ограниченным exponential backoff."""
        await self._connect()

    async def _close_consumer(self) -> None:
        consumer, self._consumer = self._consumer, None
        if consumer is not None:
            with contextlib.suppress(Exception):
                await consumer.stop()

    async def _run_with_retry(self) -> None:
        """Цикл чтения с exponential backoff при ошибках подключения к Kafka."""
        retry_delay = 1
        max_delay = 60
        retries = 0
        while True:
            try:
                await self._consume()
                raise ConnectionError("Kafka consumer завершил цикл чтения")
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
                    await self._close_consumer()
                    return

                await self._close_consumer()
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_delay)
                try:
                    await self._connect()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("KafkaConsumerRouter: переподключение не удалось")

    async def _consume(self) -> None:
        """Цикл чтения сообщений из Kafka и вызова обработчиков через safe_handle."""
        if not self._consumer:
            return

        try:
            async for msg in self._consumer:
                topic = msg.topic
                handlers = self._subscribers.get(topic, [])
                for handler in handlers:
                    log_received(
                        topic,
                        getattr(handler, "__name__", str(handler)),
                        msg.value,
                    )
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
            self._task = None
        await self._close_consumer()
        logger.info("KafkaConsumerRouter остановлен")
