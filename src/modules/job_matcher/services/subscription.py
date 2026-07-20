"""Сервис управления подписками job_matcher."""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.filters import Filter
from src.bus.interface import MessageProducer
from src.core.bus_topics import BusTopics
from src.core.clients.auth_client import AuthClient
from src.core.clients.classifier_client import ClassifierClient
from src.modules.job_matcher.constants import SUBSCRIBE_CATEGORY_PAGE_SIZE
from src.modules.job_matcher.models import Subscription
from src.modules.job_matcher.presentation.subscription import build_category_keyboard
from src.modules.job_matcher.repository import SubscriptionRepository
from src.modules.job_matcher.texts import (
    REGISTRATION_REQUIRED_MESSAGE,
    SUBSCRIPTION_CATEGORY_UNAVAILABLE_EDIT_MESSAGE,
    SUBSCRIPTION_CHOOSE_CATEGORY_PAGE_TEMPLATE,
    SUBSCRIPTION_CREATED_EDIT_TEMPLATE,
    SUBSCRIPTION_NO_CATEGORIES_MESSAGE,
)

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Читает подписки и обрабатывает пользовательский выбор категорий."""

    def __init__(
        self,
        repository: SubscriptionRepository,
        bus: MessageProducer,
    ) -> None:
        self.repository = repository
        self._bus = bus

    async def get_subscriptions(
        self,
        session: AsyncSession,
        filters: list[Filter] | None = None,
        skip: int = 0,
        limit: int = 100,
        order_by: str | None = "-created_at",
    ) -> tuple[list[Subscription], int]:
        """Получить подписки для административного API."""
        return await self.repository.get_list(session, filters, skip, limit, order_by)

    async def handle_subscribe(
        self,
        session: AsyncSession,
        chat_id: int,
        telegram_id: int,
    ) -> None:
        """Показать первую страницу категорий для подписки."""
        auth_id = await AuthClient().get_by_identifier(
            identifier=f"tg_{telegram_id}",
            session=session,
        )
        if auth_id is None:
            logger.warning(
                "Пользователь не зарегистрирован: /subscribe без /start, chat_id=%s",
                chat_id,
            )
            await self._bus.publish(
                BusTopics.BOT_MESSAGE_OUTGOING,
                {"chat_id": chat_id, "text": REGISTRATION_REQUIRED_MESSAGE},
            )
            return

        page = await ClassifierClient().get_active_categories_page(
            page=0,
            page_size=SUBSCRIBE_CATEGORY_PAGE_SIZE,
            session=session,
        )
        if not page.items:
            await self._bus.publish(
                BusTopics.BOT_MESSAGE_OUTGOING,
                {"chat_id": chat_id, "text": SUBSCRIPTION_NO_CATEGORIES_MESSAGE},
            )
            return

        await self._bus.publish(
            BusTopics.BOT_MESSAGE_OUTGOING,
            {
                "chat_id": chat_id,
                "text": SUBSCRIPTION_CHOOSE_CATEGORY_PAGE_TEMPLATE.format(
                    page=page.page + 1,
                    total_pages=page.total_pages,
                ),
                "keyboard": build_category_keyboard(
                    page.items,
                    page.page,
                    page.total_pages,
                ),
            },
        )

    async def handle_subscription_page(
        self,
        session: AsyncSession,
        chat_id: int,
        message_id: int,
        page: int,
    ) -> None:
        """Заменить клавиатуру выбора на указанную страницу категорий."""
        category_page = await ClassifierClient().get_active_categories_page(
            page=page,
            page_size=SUBSCRIBE_CATEGORY_PAGE_SIZE,
            session=session,
        )
        if not category_page.items:
            await self._bus.publish(
                BusTopics.BOT_MESSAGE_EDIT,
                {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": SUBSCRIPTION_NO_CATEGORIES_MESSAGE,
                    "keyboard": None,
                },
            )
            return

        await self._bus.publish(
            BusTopics.BOT_MESSAGE_EDIT,
            {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": SUBSCRIPTION_CHOOSE_CATEGORY_PAGE_TEMPLATE.format(
                    page=category_page.page + 1,
                    total_pages=category_page.total_pages,
                ),
                "keyboard": build_category_keyboard(
                    category_page.items,
                    category_page.page,
                    category_page.total_pages,
                ),
            },
        )

    async def handle_category_subscription(
        self,
        session: AsyncSession,
        chat_id: int,
        telegram_id: int,
        message_id: int,
        category_id: uuid.UUID,
    ) -> None:
        """Создать или дополнить подписку выбранной категорией."""
        auth_id = await AuthClient().get_by_identifier(
            identifier=f"tg_{telegram_id}",
            session=session,
        )
        if auth_id is None:
            await self._bus.publish(
                BusTopics.BOT_MESSAGE_EDIT,
                {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": REGISTRATION_REQUIRED_MESSAGE,
                    "keyboard": None,
                },
            )
            return

        category = await ClassifierClient().get_active_category(category_id, session)
        if category is None:
            await self._bus.publish(
                BusTopics.BOT_MESSAGE_EDIT,
                {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": SUBSCRIPTION_CATEGORY_UNAVAILABLE_EDIT_MESSAGE,
                    "keyboard": None,
                },
            )
            return

        subscription = await self.repository.get_by_auth_id(session, auth_id)
        category_ids = (
            [str(value) for value in subscription.category_ids or []]
            if subscription
            else []
        )
        selected_id = str(category_id)
        if selected_id not in category_ids:
            category_ids.append(selected_id)
            if subscription is None:
                await self.repository.create(
                    session,
                    {
                        "auth_id": auth_id,
                        "category_ids": category_ids,
                        "is_active": True,
                    },
                )
            else:
                await self.repository.update(
                    session,
                    subscription,
                    {"category_ids": category_ids, "is_active": True},
                )

        logger.info("Пользователь %s подписан на категорию %s", auth_id, category_id)
        await self._bus.publish(
            BusTopics.BOT_MESSAGE_EDIT,
            {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": SUBSCRIPTION_CREATED_EDIT_TEMPLATE.format(
                    category_name=category["name"]
                ),
                "keyboard": None,
            },
        )
