"""Сервис жизненного цикла пользователей job_matcher."""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.bus.interface import MessageProducer
from src.core.bus_topics import BusTopics
from src.core.clients.auth_client import AuthClient
from src.core.clients.users_client import UsersClient
from src.modules.job_bot.schemas.events import TelegramUserInfo
from src.modules.job_matcher.repository import SubscriptionRepository
from src.modules.job_matcher.texts import (
    ALREADY_REGISTERED_MESSAGE,
    WELCOME_MESSAGE,
)

logger = logging.getLogger(__name__)


class JobMatcherUserService:
    """Регистрирует и каскадно удаляет пользователей job_matcher."""

    def __init__(
        self,
        subscription_repository: SubscriptionRepository,
        bus: MessageProducer,
    ) -> None:
        self._subscription_repository = subscription_repository
        self._bus = bus

    async def delete_user(self, session: AsyncSession, auth_id: uuid.UUID) -> None:
        """Удалить подписку, профиль и учётную запись пользователя."""
        subscription = await self._subscription_repository.get_by_auth_id(
            session,
            auth_id,
        )
        if subscription is not None:
            await self._subscription_repository.delete(session, subscription)

        await UsersClient().delete_profile(auth_id, session=session)
        await AuthClient().delete_account(auth_id, session=session)

    async def handle_start(
        self,
        session: AsyncSession,
        chat_id: int,
        telegram_user: TelegramUserInfo,
    ) -> None:
        """Зарегистрировать пользователя при первом вызове /start."""
        auth_client = AuthClient()
        identifier = f"tg_{telegram_user.telegram_id}"
        existing_auth_id = await auth_client.get_by_identifier(
            identifier=identifier,
            session=session,
        )
        if existing_auth_id:
            logger.info("Пользователь уже зарегистрирован: chat_id=%s", chat_id)
            await self._bus.publish(
                BusTopics.BOT_MESSAGE_OUTGOING,
                {"chat_id": chat_id, "text": ALREADY_REGISTERED_MESSAGE},
            )
            return

        auth_id = await auth_client.register(
            identifier=identifier,
            identifier_type="telegram",
            session=session,
        )
        await UsersClient().create_profile(
            auth_id=auth_id,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
            telegram_id=telegram_user.telegram_id,
            telegram_username=telegram_user.username,
            session=session,
        )
        logger.info("Пользователь зарегистрирован: auth_id=%s", auth_id)
        await self._bus.publish(
            BusTopics.BOT_MESSAGE_OUTGOING,
            {"chat_id": chat_id, "text": WELCOME_MESSAGE},
        )
