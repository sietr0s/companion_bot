"""Behavior bus handlers."""

from typing import Any

from src.bus.interface import MessageConsumer, MessageProducer
from src.core.bus_topics import BusTopics
from src.core.database import create_async_session
from src.modules.behavior.dependencies import build_behavior_service
from src.modules.behavior.schemas.events import (
    DecideDeliveryCommand,
    DecideIntakeCommand,
    NoteDeliveryCommand,
)


def register_handlers(consumer: MessageConsumer, producer: MessageProducer) -> None:
    service = build_behavior_service(producer)

    @consumer.subscribe(BusTopics.BEHAVIOR_DECIDE_INTAKE)
    async def handle_decide_intake(message: dict[str, Any]) -> None:
        command = DecideIntakeCommand.model_validate(message)
        async with create_async_session() as session:
            await service.decide_intake(session, command)

    @consumer.subscribe(BusTopics.BEHAVIOR_DECIDE_DELIVERY)
    async def handle_decide_delivery(message: dict[str, Any]) -> None:
        command = DecideDeliveryCommand.model_validate(message)
        async with create_async_session() as session:
            await service.decide_delivery(session, command)

    @consumer.subscribe(BusTopics.BEHAVIOR_NOTE_DELIVERY)
    async def handle_note_delivery(message: dict[str, Any]) -> None:
        command = NoteDeliveryCommand.model_validate(message)
        async with create_async_session() as session:
            await service.note_delivery(session, command)
