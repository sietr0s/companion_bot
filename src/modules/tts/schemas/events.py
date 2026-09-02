"""TTS bus commands and events."""

from uuid import UUID

from pydantic import BaseModel

from src.bus.schemas import BaseEvent
from src.core.bus_topics import BusTopics


class SynthesizeCommand(BaseModel):
    account_id: UUID
    chat_id: int
    text: str


class SynthesizeSkippedEvent(BaseEvent):
    event_name: str = BusTopics.TTS_SYNTHESIZE_SKIPPED
    account_id: UUID
    chat_id: int
    reason: str = "stub"


class SynthesizedEvent(BaseEvent):
    event_name: str = BusTopics.TTS_SYNTHESIZED
    account_id: UUID
    chat_id: int
    path: str
    content_type: str = "audio/mpeg"
    generation_id: str | None = None
