from datetime import UTC, datetime

from src.modules.behavior.criteria import (
    NightVoiceCriterion,
    OutgoingLengthCriterion,
    VoiceStreakCriterion,
)
from src.modules.behavior.engine import ChatSnapshot, DecisionContext, LifeSnapshot


def test_outgoing_length_deltas():
    ctx = DecisionContext(outgoing_text=" ".join(["w"] * 16))
    d = OutgoingLengthCriterion().deltas(ctx)
    assert d["voice"] == 25.0
    assert d["text"] == -10.0


def test_voice_streak_four():
    ctx = DecisionContext(chat=ChatSnapshot(consecutive_voice_out=4, last_delivery="voice"))
    d = VoiceStreakCriterion().deltas(ctx)
    assert d["voice"] == -40.0
    assert d["text"] == 25.0


def test_night_voice_moscow_winter():
    ctx = DecisionContext(now=datetime(2026, 1, 15, 19, 0, tzinfo=UTC))
    d = NightVoiceCriterion().deltas(ctx)
    assert d["voice"] == 20.0
