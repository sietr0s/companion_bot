"""
Репозитории модуля job_matcher.

SubscriptionRepository — поиск подходящих подписок по фильтрам.
JobOfferRepository — CRUD для предложений о работе.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.repository import BaseRepository
from src.modules.job_matcher.models import JobOffer, Subscription


class SubscriptionRepository(BaseRepository[Subscription]):
    """Репозиторий подписок пользователя."""

    async def get_by_auth_id(
        self, session: AsyncSession, auth_id: uuid.UUID
    ) -> Subscription | None:
        """Найти подписку по auth_id."""
        stmt = select(Subscription).where(Subscription.auth_id == auth_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_matching(
        self,
        session: AsyncSession,
        category_ids: list[uuid.UUID] | None = None,
        tags: list[str] | None = None,
        salary_min: int | None = None,
        salary_max: int | None = None,
        location: str | None = None,
    ) -> list[Subscription]:
        """
        Найти активные подписки, подходящие под оффер.

        Используется в обработчике job.offer.classified.
        Матчинг происходит по пересечению category_ids.
        """
        stmt = select(Subscription).where(Subscription.is_active.is_(True))

        # Матчинг по категориям (пересечение множеств)
        # Если у оффера есть категории — ищем подписки где category_ids пересекается
        if category_ids:
            # Хотя бы одна категория оффера должна быть в подписке
            # subscription.category_ids && [offer_category_ids]
            category_strs = [str(cat_id) for cat_id in category_ids]

            # Строим условие: subscription.category_ids содержит хотя бы один из category_strs
            overlap_condition = None
            for cat_str in category_strs:
                cond = Subscription.category_ids.contains([cat_str])
                overlap_condition = (
                    cond if overlap_condition is None else (overlap_condition | cond)
                )

            # Пропускаем подписки где category_ids = NULL, но показываем где category_ids = []
            stmt = stmt.where(overlap_condition)

        if tags:
            # Поиск по тегам (JSON contains — работает в SQLite и PostgreSQL)
            for tag in tags:
                stmt = stmt.where(Subscription.keywords.contains(tag))
        if salary_min is not None:
            stmt = stmt.where(
                (Subscription.max_salary.is_(None)) | (Subscription.max_salary >= salary_min)
            )
        if salary_max is not None:
            stmt = stmt.where(
                (Subscription.min_salary.is_(None)) | (Subscription.min_salary <= salary_max)
            )
        if location:
            stmt = stmt.where(
                (Subscription.locations.is_(None)) | (Subscription.locations.contains([location]))
            )

        result = await session.execute(stmt)
        return list(result.scalars().all())


class JobOfferRepository(BaseRepository[JobOffer]):
    """Репозиторий предложений о работе."""

    async def get_by_source(
        self,
        session: AsyncSession,
        source_chat_id: int,
        source_message_id: int,
    ) -> JobOffer | None:
        """Найти оффер по источнику (Telegram-группа)."""
        stmt = select(JobOffer).where(
            JobOffer.source_chat_id == source_chat_id,
            JobOffer.source_message_id == source_message_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
