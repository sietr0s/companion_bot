"""
Репозитории модуля job_matcher.

SubscriptionRepository — поиск подходящих подписок по фильтрам.
JobOfferRepository — CRUD для предложений о работе.
"""

import uuid

from sqlalchemy import String, cast, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.repository import BaseRepository
from src.modules.job_matcher.models import JobOffer, Subscription


def _is_postgresql(session: AsyncSession) -> bool:
    """Проверить, что БД — PostgreSQL (для выбора правильного JSON-оператора)."""
    return session.bind.dialect.name == "postgresql" if session.bind else False


def _json_contains(session: AsyncSession, column, value: str):
    """
    JSON contains — портабельно между PostgreSQL и SQLite.

    - PostgreSQL: использует @> (JSONB contains) — точное совпадение
    - SQLite: cast к String + contains (для тестов)
    """
    if _is_postgresql(session):
        from sqlalchemy.dialects.postgresql import JSONB

        # Колонки исторически созданы как JSON, а оператор @> определён для JSONB.
        # SQL CAST нужен реально, type_coerce меняет лишь представление в SQLAlchemy.
        # Значения в этих колонках — массивы, поэтому справа также передаём массив.
        return cast(column, JSONB).contains([value])
    return cast(column, String).contains(f'"{value}"')


class SubscriptionRepository(BaseRepository[Subscription]):
    """Репозиторий подписок пользователя."""

    def __init__(self) -> None:
        super().__init__(Subscription)

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
            # PostgreSQL: @> оператор (JSONB contains) — точное совпадение
            # SQLite: cast к String + contains (для тестов)
            overlap_conditions = [
                _json_contains(session, Subscription.category_ids, cat_str)
                for cat_str in category_strs
            ]
            stmt = stmt.where(
                Subscription.category_ids.isnot(None),
                or_(*overlap_conditions),
            )

        if tags:
            tag_conditions = [
                _json_contains(session, Subscription.keywords, tag) for tag in tags
            ]
            stmt = stmt.where(
                Subscription.keywords.is_(None)
                | (cast(Subscription.keywords, String) == "null")
                | or_(*tag_conditions)
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
            stmt = stmt.where(
                (Subscription.locations.is_(None))
                | (cast(Subscription.locations, String) == "null")
                | _json_contains(session, Subscription.locations, location),
            )

        result = await session.execute(stmt)
        return list(result.scalars().all())


class JobOfferRepository(BaseRepository[JobOffer]):
    """Репозиторий предложений о работе."""

    def __init__(self) -> None:
        super().__init__(JobOffer)

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
