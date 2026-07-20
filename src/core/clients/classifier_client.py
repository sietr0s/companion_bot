"""Клиент для чтения категорий модуля classifier."""

import uuid
from dataclasses import dataclass
from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import create_async_session


@dataclass(frozen=True, slots=True)
class CategoryPage:
    """Одна страница активных категорий для пользовательского интерфейса."""

    items: list[dict]
    page: int
    total: int
    total_pages: int


class ClassifierClient:
    """Предоставляет job_matcher публичные операции с категориями."""

    @staticmethod
    async def _get_active_categories(session: AsyncSession) -> list[dict]:
        from src.modules.classifier.repository import CategoryRepository

        return await CategoryRepository().get_active_labels(session)

    async def get_active_categories(
        self,
        session: AsyncSession | None = None,
    ) -> list[dict]:
        """Получить активные категории для выбора подписки."""
        if session is not None:
            return await self._get_active_categories(session)

        async with create_async_session() as own_session:
            return await self._get_active_categories(own_session)

    async def get_active_category(
        self,
        category_id: uuid.UUID,
        session: AsyncSession | None = None,
    ) -> dict | None:
        """Получить активную категорию по ID."""
        categories = await self.get_active_categories(session)
        return next((item for item in categories if item["id"] == category_id), None)

    @staticmethod
    async def _get_active_categories_page(
        session: AsyncSession,
        page: int,
        page_size: int,
    ) -> CategoryPage:
        from src.modules.classifier.repository import CategoryRepository

        repository = CategoryRepository()
        total = await repository.count_active(session)
        total_pages = ceil(total / page_size) if total else 0
        normalized_page = min(max(page, 0), max(total_pages - 1, 0))
        items = await repository.get_active_page(
            session,
            offset=normalized_page * page_size,
            limit=page_size,
        )
        return CategoryPage(
            items=items,
            page=normalized_page,
            total=total,
            total_pages=total_pages,
        )

    async def get_active_categories_page(
        self,
        page: int,
        page_size: int,
        session: AsyncSession | None = None,
    ) -> CategoryPage:
        """Получить страницу активных категорий без загрузки полного списка."""
        if page_size <= 0:
            raise ValueError("page_size должен быть больше нуля")
        if session is not None:
            return await self._get_active_categories_page(session, page, page_size)

        async with create_async_session() as own_session:
            return await self._get_active_categories_page(own_session, page, page_size)
