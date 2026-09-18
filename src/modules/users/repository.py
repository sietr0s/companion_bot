"""Репозиторий собеседников."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.repository import BaseRepository
from src.modules.users.models import User


class UserRepository(BaseRepository[User]):
    def __init__(self) -> None:
        super().__init__(User)

    async def get_by_platform(
        self, session: AsyncSession, platform: str, platform_user_id: str
    ) -> User | None:
        result = await session.execute(
            select(User).where(
                User.platform == platform,
                User.platform_user_id == platform_user_id,
            )
        )
        return result.scalar_one_or_none()
