"""
Репозитории модуля job_matcher.

SubscriptionRepository — поиск подходящих подписок по фильтрам.
JobOfferRepository — CRUD для предложений о работе.
"""

import uuid

from sqlalchemy import or_, select, cast, String
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
        Матчинг по категориям — пересечение множеств через JSON contains.
        Матчинг по тегам — JSON contains (портабельно между SQLite и PostgreSQL).
        """

        stmt = select(Subscription).where(Subscription.is_active.is_(True))

        # Матчинг по категориям (пересечение множеств)
        # Если у оффера есть категории — ищем подписки где category_ids пересекается
        if category_ids:
            category_strs = [str(cat_id) for cat_id in category_ids]

            # Строим условие: subscription.category_ids содержит хотя бы один из category_strs
            # Используем cast к String + contains для портабельности между SQLite и PostgreSQL
            # В PostgreSQL JSON колонка приводится к тексту, в SQLite — тоже к тексту
            category_col = cast(Subscription.category_ids, String)
            overlap_conditions = [
                category_col.contains(f'"{cat_str}"')
                for cat_str in category_strs
            ]
            stmt = stmt.where(
                Subscription.category_ids.isnot(None),
                or_(*overlap_conditions),
            )

        if tags:
            tags_col = cast(Subscription.keywords, String)
            for tag in tags:
                stmt = stmt.where(
                    Subscription.keywords.isnot(None),
                    tags_col.contains(f'"{tag}"'),
                )
        if salary_min is not None:
            stmt = stmt.where(
                (Subscription.max_salary.is_(None)) | (Subscription.max_salary >= salary_min)
            )
        if salary_max is not None:
            stmt = stmt.where(
                (Subscription.min_salary.is_(None)) | (Subscription.min_salary <= salary_max)
            )
        if location:
            locations_col = cast(Subscription.locations, String)
            stmt = stmt.where(
                (Subscription.locations.is_(None))
                | (cast(Subscription.locations, String) == "null")
                | locations_col.contains(f'"{location}"'),
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
