"""STT bus commands and events."""

from uuid import UUID

from pydantic import BaseModel

from src.bus.schemas import BaseEvent
from src.core.bus_topics import BusTopics
from src.domain.chat import QuotedMessage


class TranscribeCommand(BaseModel):
    account_id: UUID
    chat_id: int
    message_id: int
    telegram_file_id: int | None = None
    media_type: str = "voice"
    reply_to: QuotedMessage | None = None
    forward_from: QuotedMessage | None = None


class TranscribedEvent(BaseEvent):
    event_name: str = BusTopics.STT_TRANSCRIBED
    account_id: UUID
    chat_id: int
    message_id: int
    text: str
    media_type: str = "voice"
    reply_to: QuotedMessage | None = None
    forward_from: QuotedMessage | None = None


class TranscribeFailedEvent(BaseEvent):
    event_name: str = BusTopics.STT_TRANSCRIBE_FAILED
    account_id: UUID
    chat_id: int
    message_id: int
    reason: str
