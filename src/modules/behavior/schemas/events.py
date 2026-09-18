"""Behavior bus commands and events."""

from uuid import UUID

from pydantic import Field

from src.bus.schemas import BaseEvent
from src.core.bus_topics import BusTopics
from src.domain.chat import Batch, ChatRef, Message


class DecideIntakeCommand(ChatRef):
    context: str = ""
    batch_messages: Batch
    recent: list[Message] = Field(default_factory=list)


class IntakeDecidedEvent(ChatRef, BaseEvent):
    event_name: str = BusTopics.BEHAVIOR_INTAKE_DECIDED
    conversation_id: UUID
    action: str
    scores: dict[str, float] = Field(default_factory=dict)
    probabilities: dict[str, float] = Field(default_factory=dict)
    activity: str | None = None
    mood: str | None = None
    needs_reply: int = 1
    asked_voice: int = 0


class DecideDeliveryCommand(ChatRef):
    messages: list[Message] = Field(default_factory=list)
    batch_messages: list[Message] = Field(default_factory=list)
    asked_voice: int = 0
    emotion: int | None = None


class DeliveryDecidedEvent(ChatRef, BaseEvent):
    event_name: str = BusTopics.BEHAVIOR_DELIVERY_DECIDED
    action: str
    text: str
    scores: dict[str, float] = Field(default_factory=dict)
    probabilities: dict[str, float] = Field(default_factory=dict)
    blocked_voice: bool = False
    block_reasons: list[str] = Field(default_factory=list)
    incoming_types: list[str] = Field(default_factory=list)
    activity: str | None = None
    mood: str | None = None


class NoteDeliveryCommand(ChatRef):
    delivery: str
