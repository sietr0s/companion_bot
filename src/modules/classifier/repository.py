"""Репозитории модуля classifier."""

from sqlalchemy import select
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
        stmt = select(Category).where(Category.is_active.is_(True))
        result = await session.execute(stmt)
        categories = result.scalars().all()
        return [{"id": cat.id, "slug": cat.slug, "name": cat.name} for cat in categories]

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
