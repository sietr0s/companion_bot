"""Схемы событий шины модуля batching."""

from src.bus.schemas import BaseEvent
from src.core.bus_topics import BusTopics
from src.domain.chat import Batch, ChatRef, Message


class AddMessageCommand(ChatRef):
    message: Message


class BatchReadyEvent(ChatRef, BaseEvent):
    event_name: str = BusTopics.BATCH_READY
    batch: Batch
