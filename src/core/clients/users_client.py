"""Прямой вызов UserService из других модулей (шина / скрипты)."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import create_async_session
from src.modules.users.models import User


class UsersClient:
    @staticmethod
    def _get_service():
        from src.bus import get_producer
        from src.modules.users.repository import UserRepository
        from src.modules.users.service import UserService

        return UserService(repository=UserRepository(), message_bus=get_producer())

    async def get_or_create(
        self,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        session: AsyncSession | None = None,
    ) -> User:
        service = self._get_service()

        async def run(current: AsyncSession) -> User:
            return await service.get_or_create_from_telegram(
                current,
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )

        if session is not None:
            return await run(session)
        async with create_async_session() as own:
            return await run(own)

    async def get_by_id(self, user_id: uuid.UUID, session: AsyncSession | None = None) -> User | None:
        service = self._get_service()
        if session is not None:
            return await service.get_by_id(session, user_id)
        async with create_async_session() as own:
            return await service.get_by_id(own, user_id)
