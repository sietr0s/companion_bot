"""
Обработчики событий модуля job_matcher.

Подписка на tg.message.received — сохранение вакансий и отправка в classifier.
Подписка на bot.message.incoming — команды /start, /subscribe.
Подписка на job.offer.classified — обновление category_ids у JobOffer и поиск подписок.
"""

import logging
import uuid

from src.bus import get_producer
from src.core.bus_topics import BusTopics
from src.core.database import async_session_factory
from src.modules.job_matcher.dependencies import get_job_matcher_service_factory

logger = logging.getLogger(__name__)


def register_handlers() -> None:
    """
    Регистрация всех обработчиков событий модуля job_matcher.

    service_factory — async callable, возвращающий (session, JobMatcherService).

    Обработчики:
    - TG_MESSAGE_RECEIVED — сохранение вакансий и отправка на классификацию
    - BOT_MESSAGE_INCOMING — диспатч команд /start и /subscribe
    - JOB_OFFER_CLASSIFIED — обновление категорий и поиск подходящих подписок
    """
    bus = get_producer()

    @bus.subscribe(BusTopics.TG_MESSAGE_RECEIVED)
    async def handle_incoming_telegram_message(message: dict) -> None:
        """Обработчик: сохранить вакансию и отправить на классификацию."""
        text = message.get("text", "")
        if not text:
            logger.warning("Пустое сообщение от Telegram: %s", message)
            return

        service = get_job_matcher_service_factory(bus=bus)

        async with async_session_factory() as session:
            job_offer = await service.save_job_offer(
                session=session,
                text=text,
                chat_id=message.get("chat_id", 0),
            )

        await service.send_for_classification(
            job_offer_id=job_offer.id,
            text=text,
        )

    @bus.subscribe(BusTopics.BOT_MESSAGE_INCOMING)
    async def handle_bot_command(message: dict) -> None:
        """Обработчик: диспатч команд /start и /subscribe."""
        chat_id = message.get("chat_id")
        command = message.get("command")

        if not chat_id:
            return

        service = get_job_matcher_service_factory(bus=bus)

        async with async_session_factory() as session:
            if command == "/start":
                await service.handle_start(session=session, chat_id=chat_id)
            elif command == "/subscribe":
                await service.handle_subscribe(session=session, chat_id=chat_id)

    @bus.subscribe(BusTopics.JOB_OFFER_CLASSIFIED)
    async def handle_job_offer_classified(message: dict) -> None:
        """
        Обработчик: обновить category_ids и найти подходящие подписки.

        message: {
            "request_id": str (UUID),
            "category_ids": list[uuid.UUID],
            "title": str,
            "tags": list[str],
            "salary_from": int,
            "salary_to": int,
            "location": str,
        }
        """
        category_ids = message.get("category_ids", [])
        request_id = message.get("request_id")

        if not request_id:
            logger.warning("Нет request_id в сообщении: %s", message)
            return

        # Преобразуем request_id в UUID
        try:
            job_offer_id = uuid.UUID(request_id)
        except (ValueError, TypeError):
            logger.warning("Некорректный request_id: %s", request_id)
            return

        service = get_job_matcher_service_factory(bus=bus)

        async with async_session_factory() as session:
            # 1. Обновляем категории у вакансии
            await service.update_job_offer_categories(
                session=session,
                job_offer_id=job_offer_id,
                category_ids=category_ids,
            )

        async with async_session_factory() as session:
            # 2. Ищем подходящие подписки и отправляем уведомления
            await service.handle_offer_classified(
                session=session,
                title=message.get("title", ""),
                category_ids=category_ids,
                tags=message.get("tags", []),
                salary_from=message.get("salary_from"),
                salary_to=message.get("salary_to"),
                location=message.get("location"),
            )
