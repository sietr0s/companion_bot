"""
Kafka-реализация продюсера шины сообщений.

Используется при переходе к микросервисной архитектуре.
Сообщения сериализуются в JSON и отправляются в Kafka-топик.
При старте ждёт готовности Kafka с экспоненциальным backoff.
"""

import json
import logging
from typing import Any

import backoff
from aiokafka import AIOKafkaProducer

from src.core.config import settings

logger = logging.getLogger(__name__)


class KafkaProducerBus:
    """
    Kafka-продюсер: отправляет сообщения в топики Kafka.

    Также хранит реестр локальных подписчиков для единообразия
    с InMemoryProducer (полезно при гибридном режиме).
    """

    def __init__(self) -> None:
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        """Инициализация и запуск Kafka-продюсера с retry."""

        @backoff.on_exception(
            backoff.expo,
            Exception,
            max_time=60,
            on_backoff=lambda details: logger.warning(
                "Kafka недоступен (попытка %d): %s. Повтор через %.1fс...",
                details["tries"],
                details["exception"],
                details["wait"],
            ),
        )
        async def _connect() -> None:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            await self._producer.start()

        await _connect()
        logger.info("KafkaProducerBus запущен")

    async def stop(self) -> None:
        """Остановка Kafka-продюсера."""
        if self._producer:
            await self._producer.stop()
            logger.info("KafkaProducerBus остановлен")

    async def publish(self, topic: str, message: dict[str, Any]) -> None:
        """
        Отправка сообщения в Kafka-топик.

        send_and_wait — гарантированная отправка
        с подтверждением от брокера.

        """
        if not self._producer:
            logger.error("Kafka-продюсер не инициализирован")
            return

        await self._send_message(topic, message)

    async def _send_message(self, topic: str, message: dict[str, Any]) -> None:
        """Внутренний метод для асинхронной отправки."""
        if self._producer:
            await self._producer.send_and_wait(topic, message)
            logger.info("Сообщение отправлено в топик '%s'", topic)
