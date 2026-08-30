"""Репозиторий для Example модуля."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.repository import BaseRepository
from src.modules.example.model import ExampleModel


class ExampleRepository(BaseRepository[ExampleModel]):
    """Репозиторий для работы с Example."""

    def __init__(self) -> None:
        super().__init__(ExampleModel)

    async def get_by_name(self, session: AsyncSession, name: str) -> ExampleModel | None:
        """Найти Example по имени."""
        stmt = select(ExampleModel).where(ExampleModel.name == name)
        result = await session.execute(stmt)
        return result.scalars().first()
