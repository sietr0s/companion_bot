"""Repositories for Instagram accounts, settings, and chat state."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.repository import BaseRepository
from src.modules.instagram_clients.models import (
    InstagramAccount,
    InstagramChatState,
    InstagramSettings,
)


class InstagramAccountRepository(BaseRepository[InstagramAccount]):
    def __init__(self) -> None:
        super().__init__(InstagramAccount)

    async def get_connected_accounts(self, session: AsyncSession) -> list[InstagramAccount]:
        stmt = select(InstagramAccount).where(InstagramAccount.is_connected.is_(True))
        result = await session.execute(stmt)
        return list(result.scalars().all())


class InstagramSettingsRepository(BaseRepository[InstagramSettings]):
    def __init__(self) -> None:
        super().__init__(InstagramSettings)

    async def get_by_account_id(
        self, session: AsyncSession, account_id: uuid.UUID
    ) -> InstagramSettings | None:
        stmt = select(self.model).where(self.model.account_id == account_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


class InstagramChatStateRepository(BaseRepository[InstagramChatState]):
    def __init__(self) -> None:
        super().__init__(InstagramChatState)

    async def get_by_account_and_thread(
        self,
        session: AsyncSession,
        account_id: uuid.UUID,
        thread_id: int,
    ) -> InstagramChatState | None:
        stmt = select(self.model).where(
            self.model.account_id == account_id,
            self.model.thread_id == thread_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_last_item_id(
        self,
        session: AsyncSession,
        account_id: uuid.UUID,
        thread_id: int,
        item_id: str,
    ) -> InstagramChatState:
        existing = await self.get_by_account_and_thread(session, account_id, thread_id)
        if existing:
            return await self.update(session, existing, {"last_item_id": item_id})
        return await self.create(
            session,
            {
                "account_id": account_id,
                "thread_id": thread_id,
                "last_item_id": item_id,
            },
        )

    async def get_all_by_account(
        self, session: AsyncSession, account_id: uuid.UUID
    ) -> list[InstagramChatState]:
        stmt = select(self.model).where(self.model.account_id == account_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())
