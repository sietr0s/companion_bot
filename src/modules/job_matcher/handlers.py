"""
Обработчики событий модуля job_matcher.

Подписка на tg.message.received — сохранение вакансий и отправка в classifier.
Подписка на bot.message.incoming — команды /start, /subscribe.
Подписка на job.offer.classified — обновление category_ids у JobOffer и поиск подписок.
"""

import logging
import uuid

from src.bus import get_consumer
from src.bus.interface import MessageConsumer
from src.core.bus_topics import BusTopics
from src.core.database import create_async_session
from src.modules.job_bot.schemas.events import BotMessageIncoming
from src.modules.job_matcher.constants import (
    SUBSCRIBE_CATEGORY_CALLBACK_PREFIX,
    SUBSCRIBE_PAGE_CALLBACK_PREFIX,
    SUBSCRIBE_PAGE_NOOP_CALLBACK,
)
from src.modules.job_matcher.dependencies import (
    get_job_matcher_user_service_factory,
    get_job_offer_service_factory,
    get_subscription_service_factory,
)

logger = logging.getLogger(__name__)


def register_handlers(
    consumer: MessageConsumer | None = None,
) -> None:
    """
    Регистрация всех обработчиков событий модуля job_matcher.

    Обработчики:
    - TG_MESSAGE_RECEIVED — сохранение вакансий и отправка на классификацию
    - BOT_MESSAGE_INCOMING — диспатч команд /start и /subscribe
    - JOB_OFFER_CLASSIFIED — обновление категорий и поиск подходящих подписок
    """
    consumer = consumer or get_consumer()

    @consumer.subscribe(BusTopics.TG_MESSAGE_RECEIVED)
    async def handle_incoming_telegram_message(message: dict) -> None:
        """Обработчик: сохранить вакансию и отправить на классификацию."""
        text = message.get("text", "")
        if not text:
            logger.warning("Пустое сообщение от Telegram: %s", message)
            return

        service = get_job_offer_service_factory()

        async with create_async_session() as session:
            job_offer = await service.save_job_offer(
                session=session,
                text=text,
                chat_id=message.get("chat_id", 0),
                message_id=message.get("message_id", 0),
                sender=message["sender"],
            )

        await service.send_for_classification(
            job_offer_id=job_offer.id,
            text=text,
        )

    @consumer.subscribe(BusTopics.BOT_MESSAGE_INCOMING)
    async def handle_bot_command(message: dict) -> None:
        """Обработчик: диспатч команд /start и /subscribe."""
        event = BotMessageIncoming.model_validate(message)

        subscription_service = get_subscription_service_factory()
        user_service = get_job_matcher_user_service_factory()

        async with create_async_session() as session:
            if event.callback_data == SUBSCRIBE_PAGE_NOOP_CALLBACK:
                return
            if event.callback_data and event.callback_data.startswith(
                SUBSCRIBE_PAGE_CALLBACK_PREFIX
            ):
                if event.message_id is None:
                    logger.warning("Callback пагинации не содержит message_id")
                    return
                try:
                    page = int(
                        event.callback_data.removeprefix(
                            SUBSCRIBE_PAGE_CALLBACK_PREFIX
                        )
                    )
                except ValueError:
                    logger.warning(
                        "Некорректный callback страницы категорий: %s",
                        event.callback_data,
                    )
                    return
                await subscription_service.handle_subscription_page(
                    session=session,
                    chat_id=event.chat_id,
                    message_id=event.message_id,
                    page=page,
                )
            elif event.callback_data and event.callback_data.startswith(
                SUBSCRIBE_CATEGORY_CALLBACK_PREFIX
            ):
                if event.message_id is None:
                    logger.warning("Callback выбора категории не содержит message_id")
                    return
                try:
                    category_id = uuid.UUID(
                        event.callback_data.removeprefix(
                            SUBSCRIBE_CATEGORY_CALLBACK_PREFIX
                        )
                    )
                except ValueError:
                    logger.warning(
                        "Некорректный callback выбора категории: %s",
                        event.callback_data,
                    )
                    return
                await subscription_service.handle_category_subscription(
                    session=session,
                    chat_id=event.chat_id,
                    telegram_id=event.user.telegram_id,
                    message_id=event.message_id,
                    category_id=category_id,
                )
            elif event.command == "/start":
                await user_service.handle_start(
                    session=session,
                    chat_id=event.chat_id,
                    telegram_user=event.user,
                )
            elif event.command == "/subscribe":
                await subscription_service.handle_subscribe(
                    session=session,
                    chat_id=event.chat_id,
                    telegram_id=event.user.telegram_id,
                )

    @consumer.subscribe(BusTopics.JOB_OFFER_CLASSIFIED)
    async def handle_job_offer_classified(message: dict) -> None:
        """
        Обработчик: обновить category_ids и найти подходящие подписки.

        message: {
            "request_id": str (UUID),
            "category_ids": list[uuid.UUID],
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

        service = get_job_offer_service_factory()

        async with create_async_session() as session:
            # 1. Обновляем категории у вакансии
            await service.update_job_offer_categories(
                session=session,
                job_offer_id=job_offer_id,
                category_ids=category_ids,
            )

        async with create_async_session() as session:
            # 2. Ищем подходящие подписки и отправляем уведомления
            await service.handle_offer_classified(
                session=session,
                job_offer_id=job_offer_id,
                category_ids=category_ids,
                tags=message.get("tags", []),
                salary_from=message.get("salary_from"),
                salary_to=message.get("salary_to"),
                location=message.get("location"),
            )
