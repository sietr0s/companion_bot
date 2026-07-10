"""Обработчики событий модуля classifier."""

import logging
import uuid

from src.bus.interface import MessageBus
from src.core.bus_topics import BusTopics
from src.core.database import async_session_factory
from src.modules.classifier.service import ClassifierService

logger = logging.getLogger(__name__)


async def init_default_categories_on_startup() -> None:
    """
    Инициализация категорий по умолчанию при старте.

    Вызывается один раз при запуске приложения.
    """
    from src.modules.classifier.repository import CategoryRepository

    async with async_session_factory() as session:
        service = ClassifierService(
            repository=CategoryRepository(),
            log_repository=None,
            message_bus=None,
            category_classifier=None,
            entity_extractor=None,
        )
        await service.init_default_categories(session)
        await session.commit()


def register_handlers(
    bus: MessageBus,
    service_factory,
) -> None:
    """
    Регистрация обработчиков событий на шину.

    service_factory — async callable, возвращающий кортеж (session, ClassifierService).
    """

    @bus.subscribe(BusTopics.TEXT_CLASSIFY_REQUEST)
    async def handle_classify_request(message: dict) -> None:
        """Обработчик: классифицировать текст."""
        request_id_str = message.get("request_id")
        text = message.get("text")

        if not request_id_str or not text:
            logger.warning("Неполные данные для классификации: %s", message)
            return

        request_id = uuid.UUID(request_id_str)

        # Получаем сессию и сервис
        async with async_session_factory() as session:
            service: ClassifierService = service_factory(session)
            result = await service.process_classify_request(
                session=session,
                request_id=request_id,
                text=text,
            )
            await session.commit()

            # Публикуем событие с результатом классификации
            if result:
                await bus.publish(
                    BusTopics.JOB_OFFER_CLASSIFIED,
                    {
                        "request_id": str(request_id),
                        "category_ids": result.get("category_ids", []),
                        "categories": result.get("categories", []),
                    },
                )
