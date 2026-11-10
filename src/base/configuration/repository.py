"""Atomic singleton updates. The service owns the transaction."""

from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.configuration.model import BaseConfigModel
from src.core.exceptions import ConflictError

Model = TypeVar("Model", bound=BaseConfigModel)


class BaseConfigRepository(Generic[Model]):
    def __init__(self, model: type[Model]):
        self.model = model

    async def initialize(self, session: AsyncSession) -> None:
        dialect = session.get_bind().dialect.name
        insert = sqlite_insert if dialect == "sqlite" else pg_insert
        await session.execute(
            insert(self.model)
            .values(id=1, revision=0, overrides={})
            .on_conflict_do_nothing(index_elements=["id"])
        )

    async def read(self, session: AsyncSession) -> Model:
        row = await session.get(self.model, 1, populate_existing=True)
        if row is None:
            await self.initialize(session)
            row = await session.get(self.model, 1, populate_existing=True)
        if row is None:
            raise RuntimeError("Configuration singleton was not initialized")
        return row

    async def replace(
        self, session: AsyncSession, revision: int, values: dict[str, Any], actor: UUID
    ) -> None:
        result = await session.execute(
            update(self.model)
            .where(self.model.id == 1, self.model.revision == revision)
            .values(overrides=values, revision=revision + 1, updated_by=actor)
            .returning(self.model.id)
        )
        if result.scalar_one_or_none() is None:
            raise ConflictError("Configuration changed; reload it before saving")
