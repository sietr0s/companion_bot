"""Behavior bus commands and events."""

from uuid import UUID

from pydantic import BaseModel, Field

from src.bus.schemas import BaseEvent
from src.core.bus_topics import BusTopics
from src.domain.chat import Message


class DecideIntakeCommand(BaseModel):
    conversation_id: UUID
    telegram_account_id: UUID | None = None
    telegram_chat_id: int
    context: str = ""
    batch_messages: list[Message] = Field(default_factory=list)


class IntakeDecidedEvent(BaseEvent):
    event_name: str = BusTopics.BEHAVIOR_INTAKE_DECIDED
    conversation_id: UUID
    telegram_account_id: UUID | None = None
    telegram_chat_id: int
    action: str
    scores: dict[str, float] = Field(default_factory=dict)
    activity: str | None = None
    mood: str | None = None
    needs_reply: int = 1
    asked_voice: int = 0


class DecideDeliveryCommand(BaseModel):
    conversation_id: UUID | None = None
    telegram_account_id: UUID | None = None
    telegram_chat_id: int
    messages: list[Message] = Field(default_factory=list)
    batch_messages: list[Message] = Field(default_factory=list)
    asked_voice: int = 0
    emotion: int | None = None


class DeliveryDecidedEvent(BaseEvent):
    event_name: str = BusTopics.BEHAVIOR_DELIVERY_DECIDED
    conversation_id: UUID | None = None
    telegram_account_id: UUID | None = None
    telegram_chat_id: int
    action: str
    text: str
    scores: dict[str, float] = Field(default_factory=dict)
    blocked_voice: bool = False
    block_reasons: list[str] = Field(default_factory=list)


class NoteDeliveryCommand(BaseModel):
    telegram_account_id: UUID
    telegram_chat_id: int
    channel: str
