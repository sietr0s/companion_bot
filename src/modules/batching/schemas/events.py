"""Схемы событий шины модуля batching."""

from uuid import UUID

from pydantic import BaseModel, Field

from src.core.bus_topics import BusTopics


class AddMessageCommand(BaseModel):
    telegram_chat_id: int
    telegram_account_id: UUID
    content: str
    sequence_number: int | None = None


class BatchReadyEvent(BaseModel):
    batch_id: UUID
    telegram_chat_id: int
    telegram_account_id: UUID
    messages: list[str] = Field(default_factory=list)
    message_count: int = 0

    def to_bus_dict(self) -> dict:
        data = self.model_dump(mode="json")
        data["event_name"] = BusTopics.BATCH_READY
        return data


class BatchCompletedEvent(BaseModel):
    batch_id: UUID
    telegram_chat_id: int
    success: bool
    error_message: str | None = None

    def to_bus_dict(self) -> dict:
        data = self.model_dump(mode="json")
        data["event_name"] = BusTopics.BATCH_COMPLETED
        return data
