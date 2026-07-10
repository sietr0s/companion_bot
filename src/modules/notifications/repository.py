"""
Репозитории модуля нотификаций.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.repository import BaseRepository
from src.modules.notifications.models import NotificationLog, NotificationTemplate


class NotificationTemplateRepository(BaseRepository[NotificationTemplate]):
    """Репозиторий шаблонов уведомлений."""

    def __init__(self) -> None:
        super().__init__(NotificationTemplate)

    async def get_by_name(
        self, session: AsyncSession, name: str, channel: str = "email"
    ) -> NotificationTemplate | None:
        """Найти активный шаблон по имени и каналу."""
        stmt = select(NotificationTemplate).where(
            NotificationTemplate.name == name,
            NotificationTemplate.channel == channel,
            NotificationTemplate.is_active.is_(True),
        )
        result = await session.execute(stmt)
        return result.scalars().first()


class NotificationLogRepository(BaseRepository[NotificationLog]):
    """Репозиторий логов уведомлений."""

    def __init__(self) -> None:
        super().__init__(NotificationLog)

    async def get_by_auth_id(
        self, session: AsyncSession, auth_id: uuid.UUID, limit: int = 50
    ) -> list[NotificationLog]:
        """Получить лог уведомлений пользователя."""
        stmt = (
            select(NotificationLog)
            .where(NotificationLog.auth_id == auth_id)
            .order_by(NotificationLog.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
