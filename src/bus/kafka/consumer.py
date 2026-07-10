"""
Kafka-реализация консьюмера шины сообщений.

Подписывается на топики Kafka и вызывает зарегистрированные
обработчики при получении сообщений.
"""

import asyncio
import json
import logging
from collections.abc import Callable

from aiokafka import AIOKafkaConsumer

from src.core.config import settings

logger = logging.getLogger(__name__)


class KafkaConsumerRouter:
    """
    Kafka-консьюмер: слушает топики и вызывает обработчики.

    Получает реестр подписчиков от продюсера и подписывается
    на соответствующие топики Kafka.
    """

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

        self._consumer = AIOKafkaConsumer(
            *topics,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_GROUP_ID,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )
        await self._consumer.start()
        # Запускаем цикл чтения в фоновой задаче
        self._task = asyncio.create_task(self._consume())
        logger.info("KafkaConsumerRouter запущен, топики: %s", topics)

    async def _consume(self) -> None:
        """Цикл чтения сообщений из Kafka и вызова обработчиков."""
        if not self._consumer:
            return

        try:
            async for msg in self._consumer:
                topic = msg.topic
                handlers = self._subscribers.get(topic, [])
                for handler in handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(msg.value)
                        else:
                            handler(msg.value)
                    except asyncio.CancelledError:
                        logger.warning("Обработчик %s отменён для топика '%s'", handler.__name__, topic)
                        raise
                    except Exception as e:
                        logger.exception(
                            "Ошибка в обработчике %s для топика '%s': %s",
                            handler.__name__,
                            topic,
                            e,
                        )
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
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._consumer:
            await self._consumer.stop()
            logger.info("KafkaConsumerRouter остановлен")
