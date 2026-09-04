from uuid import uuid4

from src.core.bus_topics import BusTopics
from src.core.config import Settings
from src.modules.behavior.schemas.events import IntakeDecidedEvent


def test_behavior_topics_exist():
    assert BusTopics.BEHAVIOR_DECIDE_INTAKE == "behavior.command.decide_intake"
    assert BusTopics.TG_MESSAGE_SEND_VOICE == "telegram_clients.command.send_voice"


def test_behavior_settings_defaults():
    s = Settings(JWT_SECRET_KEY="t", ADMIN_EMAIL="a@b.c", ADMIN_PASSWORD="p")
    assert s.BEHAVIOR_TIMEZONE == "Europe/Moscow"
    assert s.BEHAVIOR_SOFTMAX_TEMP == 1.0
    assert s.BEHAVIOR_INTAKE_TIMEOUT_S == 8.0


def test_intake_event_roundtrip():
    ev = IntakeDecidedEvent(
        conversation_id=uuid4(),
        telegram_chat_id=1,
        action="respond",
    )
    data = ev.to_bus_dict()
    assert data["event_name"] == BusTopics.BEHAVIOR_INTAKE_DECIDED
