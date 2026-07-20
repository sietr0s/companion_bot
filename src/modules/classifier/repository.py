"""Репозитории модуля classifier."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.repository import BaseRepository
from src.modules.classifier.models import Category, ClassificationLog


class CategoryRepository(BaseRepository[Category]):
    """Репозиторий категорий классификатора."""

    def __init__(self) -> None:
        super().__init__(Category)

    async def get_active_labels(self, session: AsyncSession) -> list[dict]:
        """
        Получить активные категории для классификации.

        Returns:
            [{"id": UUID, "slug": str, "name": str}, ...]
        """
        stmt = (
            select(Category)
            .where(Category.is_active.is_(True))
            .order_by(Category.name)
        )
        result = await session.execute(stmt)
        categories = result.scalars().all()
        return [{"id": cat.id, "slug": cat.slug, "name": cat.name} for cat in categories]

    async def count_active(self, session: AsyncSession) -> int:
        """Количество активных категорий."""
        stmt = select(func.count()).select_from(Category).where(Category.is_active.is_(True))
        return int((await session.execute(stmt)).scalar_one())

    async def get_active_page(
        self,
        session: AsyncSession,
        offset: int,
        limit: int,
    ) -> list[dict]:
        """Получить стабильную страницу активных категорий, отсортированную по имени."""
        stmt = (
            select(Category)
            .where(Category.is_active.is_(True))
            .order_by(Category.name, Category.id)
            .offset(offset)
            .limit(limit)
        )
        categories = (await session.execute(stmt)).scalars().all()
        return [{"id": item.id, "slug": item.slug, "name": item.name} for item in categories]

    async def get_by_slug(self, session: AsyncSession, slug: str) -> Category | None:
        """Получить категорию по слагy."""
        stmt = select(Category).where(Category.slug == slug)
        result = await session.execute(stmt)
        return result.scalars().first()

    async def get_by_name(self, session: AsyncSession, name: str) -> Category | None:
        """Получить категорию по имени."""
        stmt = select(Category).where(Category.name == name)
        result = await session.execute(stmt)
        return result.scalars().first()


class ClassificationLogRepository(BaseRepository[ClassificationLog]):
    """Репозиторий логов классификации."""

    def __init__(self) -> None:
        super().__init__(ClassificationLog)
