"""Validation and persisted overrides are separate from runtime snapshots."""

from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.configuration.contracts import ConfigRead
from src.base.configuration.model import BaseConfigModel
from src.base.configuration.repository import BaseConfigRepository
from src.base.configuration.schema import BaseModuleConfig
from src.core.exceptions import ValidationError

Config = TypeVar("Config", bound=BaseModuleConfig)
Model = TypeVar("Model", bound=BaseConfigModel)


class BaseConfigService(Generic[Config, Model]):
    def __init__(self, schema: type[Config], repository: BaseConfigRepository[Model]):
        self.schema = schema
        self.repository = repository

    def resolve(self, overrides: dict[str, Any]) -> Config:
        environment = self.schema()
        known = {key: value for key, value in overrides.items() if key in self.schema.model_fields}
        return self.schema.model_validate({**environment.model_dump(), **known})

    async def read(self, session: AsyncSession) -> ConfigRead:
        row = await self.repository.read(session)
        config = self.resolve(row.overrides)
        environment = self.schema()
        known = self.schema.model_fields
        return ConfigRead(
            revision=row.revision,
            values=config.model_dump(mode="json"),
            overrides={k: v for k, v in row.overrides.items() if k in known},
            sources={
                k: "database"
                if k in row.overrides
                else "environment"
                if k in environment.model_fields_set
                else "default"
                for k in known
            },
            obsolete_keys=sorted(set(row.overrides) - set(known)),
            field_schema=self.schema.model_json_schema(),
        )

    async def change(
        self,
        session: AsyncSession,
        revision: int,
        values: dict[str, Any],
        actor: UUID,
        *,
        reset: bool = False,
    ) -> ConfigRead:
        try:
            row = await self.repository.read(session)
            allowed = set(self.schema.model_fields) | (set(row.overrides) if reset else set())
            if set(values) - allowed:
                raise ValidationError("Unknown configuration fields")
            merged = dict(row.overrides)
            if reset:
                for key in values:
                    merged.pop(key, None)
            else:
                merged.update(values)
            try:
                self.resolve(merged)
            except PydanticValidationError as error:
                raise ValidationError(str(error)) from error
            await self.repository.replace(session, revision, merged, actor)
            await session.flush()
            result = await self.read(session)
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise

    async def load_snapshot(self, session: AsyncSession) -> Config:
        """Startup errors propagate; never fall back when stored data is invalid."""
        row = await self.repository.read(session)
        snapshot = self.resolve(row.overrides)
        await session.commit()
        return snapshot
