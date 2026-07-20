"""Обработчики событий модуля classifier."""

import logging
import uuid
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from sqlalchemy.ext.asyncio import AsyncSession

from src.bus import configure_bus, get_consumer, get_producer
from src.bus.interface import MessageConsumer, MessageProducer
from src.core.bus_topics import BusTopics
from src.core.database import create_async_session
from src.modules.classifier.dependencies import get_classifier_service_factory
from src.modules.classifier.service import ClassifierService

logger = logging.getLogger(__name__)


async def init_default_categories_on_startup() -> None:
    """
    Инициализация категорий по умолчанию при старте.

    Вызывается один раз при запуске приложения.
    """
    from src.modules.classifier.repository import CategoryRepository

    async with create_async_session() as session:
        service = ClassifierService(
            repository=CategoryRepository(),
            log_repository=None,
            message_bus=None,
            category_classifier=None,
            entity_extractor=None,
        )
        await service.init_default_categories(session)


def register_handlers(
    consumer: MessageConsumer | None = None,
    producer: MessageProducer | None = None,
    session_factory: Callable[[], AbstractAsyncContextManager[AsyncSession]] | None = None,
) -> None:
    """
    Регистрация обработчиков событий на шину.

    service_factory — async callable, возвращающий кортеж (session, ClassifierService).
    """
    consumer = consumer or get_consumer()
    if producer is None:
        producer = get_producer()
    else:
        configure_bus(producer, consumer)

    def create_session() -> AbstractAsyncContextManager[AsyncSession]:
        if session_factory is not None:
            return session_factory()
        return create_async_session()

    @consumer.subscribe(BusTopics.TEXT_CLASSIFY_REQUEST)
    async def handle_classify_request(message: dict) -> None:
        """Обработчик: классифицировать текст."""
        request_id_str = message.get("request_id")
        text = message.get("text")

        if not request_id_str or not text:
            logger.warning("Неполные данные для классификации: %s", message)
            return

        request_id = uuid.UUID(request_id_str)

        # Получаем сессию и сервис
        service: ClassifierService = get_classifier_service_factory()
        async with create_session() as session:
            result = await service.process_classify_request(
                session=session,
                request_id=request_id,
                text=text,
            )

            # Публикуем событие с результатом классификации
            if result:
                await producer.publish(
                    BusTopics.JOB_OFFER_CLASSIFIED,
                    {
                        "request_id": str(request_id),
                        "category_ids": result.get("category_ids", []),
                        "categories": result.get("categories", []),
                    },
                )
