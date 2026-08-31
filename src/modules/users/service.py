"""Собеседники Telegram: upsert из входящих сообщений и CRUD."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.service import BaseService
from src.bus.interface import MessageProducer
from src.core.bus_topics import BusTopics
from src.modules.users.models import User
from src.modules.users.repository import UserRepository
from src.modules.users.schemas.events import UserCreated, UserUpdated


class UserService(BaseService[UserRepository, User]):
    def __init__(self, repository: UserRepository, message_bus: MessageProducer) -> None:
        super().__init__(repository)
        self.message_bus = message_bus

    async def get_or_create_from_telegram(
        self,
        session: AsyncSession,
        *,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> User:
        existing = await self.repository.get_by_telegram_id(session, telegram_id)
        incoming = {
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
        }
        if existing is None:
            user = await self.repository.create(
                session,
                {"telegram_id": telegram_id, **incoming},
            )
            await self.message_bus.publish(
                BusTopics.USER_CREATED,
                UserCreated(
                    user_id=user.id,
                    telegram_id=user.telegram_id,
                ).to_bus_dict(),
            )
            return user

        changes = {
            field: value
            for field, value in incoming.items()
            if value is not None and getattr(existing, field) != value
        }
        if not changes:
            return existing
        user = await self.repository.update(session, existing, changes)
        await self.message_bus.publish(
            BusTopics.USER_UPDATED,
            UserUpdated(
                user_id=user.id,
                telegram_id=user.telegram_id,
                fields_updated=list(changes),
            ).to_bus_dict(),
        )
        return user
