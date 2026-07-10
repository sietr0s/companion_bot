"""
Базовый репозиторий — обобщённый (дженерик) класс для CRUD-операций.

Репозиторий инкапсулирует работу с SQLAlchemy, изолируя
бизнес-логику от деталей ORM. При выносе модуля в микросервис
достаточно заменить реализацию репозитория (например, на HTTP-клиент),
не меняя сервисный слой.
"""

from collections.abc import Sequence
from typing import Generic, TypeVar

from pydantic import BaseModel as PydanticModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.filters import Filter, apply_filters
from src.base.model import BaseModel

# Тип модели, с которой работает репозиторий
ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    """
    Дженерик-репозиторий с набором стандартных CRUD-операций.

    Конкретные репозитории наследуются от него и добавляют
    специфичные запросы (например, get_by_email).
    """

    def __init__(self, model: type[ModelType]):
        self.model = model

    async def get_by_id(self, session: AsyncSession, id: object) -> ModelType | None:
        """Получить сущность по первичному ключу."""
        return await session.get(self.model, id)

    async def get_all(
        self, session: AsyncSession, skip: int = 0, limit: int = 100
    ) -> Sequence[ModelType]:
        """Получить список сущностей с пагинацией."""
        stmt = select(self.model).offset(skip).limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def count(
        self,
        session: AsyncSession,
        filters: list[Filter] | None = None,
    ) -> int:
        """Подсчитать количество записей с учётом фильтров."""
        stmt = select(func.count()).select_from(self.model)
        if filters:
            stmt = apply_filters(stmt, self.model, filters)
        result = await session.execute(stmt)
        return result.scalar() or 0

    async def get_list(
        self,
        session: AsyncSession,
        filters: list[Filter] | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[ModelType], int]:
        """
        Получить список сущностей с фильтрацией и пагинацией.

        Возвращает кортеж (items, total) — total для вычисления страниц.
        """
        stmt = select(self.model)
        if filters:
            stmt = apply_filters(stmt, self.model, filters)

        # Сначала считаем total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await session.execute(count_stmt)
        total = total_result.scalar() or 0

        # Потом получаем данные
        stmt = stmt.offset(skip).limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all(), total

    async def create(self, session: AsyncSession, data: dict | PydanticModel) -> ModelType:
        """
        Создать новую сущность.

        Принимает как словарь, так и Pydantic-модель.
        Если передана Pydantic-модель — используем model_dump()
        для получения словаря с данными.
        """
        if isinstance(data, PydanticModel):
            values = data.model_dump(exclude_unset=True)
        else:
            values = data

        instance = self.model(**values)
        session.add(instance)
        await session.commit()
        await session.refresh(instance)
        return instance

    async def update(
        self,
        session: AsyncSession,
        db_obj: ModelType,
        data: dict | PydanticModel,
    ) -> ModelType:
        """
        Обновить существующую сущность.

        Обновляются только переданные поля (partial update).
        exclude_unset=True гарантирует, что None-значения
        не затрут существующие данные.
        """
        if isinstance(data, PydanticModel):
            values = data.model_dump(exclude_unset=True)
        else:
            values = data

        for field, value in values.items():
            setattr(db_obj, field, value)

        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def delete(self, session: AsyncSession, db_obj: ModelType) -> None:
        """Удалить сущность из БД."""
        await session.delete(db_obj)
        await session.commit()
