"""Сервис для Example модуля."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from src.base.service import BaseService
from src.bus.interface import MessageProducer
from src.core.bus_topics import BusTopics
from src.modules.example.model import ExampleModel
from src.modules.example.repository import ExampleRepository
from src.modules.example.schemas_bus import ExampleCreatedEvent, ExampleDeletedEvent, ExampleUpdatedEvent


class ExampleService(BaseService[ExampleRepository, ExampleModel]):
    """Сервис для работы с Example."""

    def __init__(self, repository: ExampleRepository, message_bus: MessageProducer):
        super().__init__(repository)
        self.message_bus = message_bus

    async def get_by_id(
        self,
        session: AsyncSession,
        entity_id: UUID,
    ) -> ExampleModel | None:
        """Получить Example по ID."""
        return await super().get_by_id(session, entity_id)

    async def get_all(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ExampleModel]:
        """Получить список Example."""
        return await super().get_all(session, skip, limit)

    async def create(
        self,
        session: AsyncSession,
        data: dict[str, Any],
    ) -> ExampleModel:
        """Создать Example и опубликовать событие."""
        result = await super().create(session, data)
        
        # Публикуем событие о создании
        event = ExampleCreatedEvent(id=result.id, name=result.name)
        await self.message_bus.publish(BusTopics.EXAMPLE_CREATED, {event.event_name: event.model_dump()})
        
        return result

    async def update(
        self,
        session: AsyncSession,
        obj_id: UUID,
        data: dict[str, Any],
    ) -> ExampleModel:
        """Обновить Example и опубликовать событие."""
        result = await super().update(session, obj_id, data)
        
        # Публикуем событие об обновлении
        event = ExampleUpdatedEvent(id=result.id, name=result.name)
        await self.message_bus.publish(BusTopics.EXAMPLE_UPDATED, {event.event_name: event.model_dump()})
        
        return result

    async def delete(self, session: AsyncSession, obj_id: UUID) -> None:
        """Удалить Example и опубликовать событие."""
        # Сначала получаем объект для события
        obj = await self.get_by_id(session, obj_id)
        if obj:
            await super().delete(session, obj_id)
            
            # Публикуем событие об удалении
            event = ExampleDeletedEvent(id=obj.id)
            await self.message_bus.publish(BusTopics.EXAMPLE_DELETED, {event.event_name: event.model_dump()})
