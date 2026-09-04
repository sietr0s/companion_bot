"""Scoring parameters: one class per criterion."""

from __future__ import annotations

from src.core.config import settings
from src.modules.behavior.engine import DecisionContext
from src.modules.behavior.scoring import is_night, is_short_greeting, word_count


class NeedsReplyCriterion:
    name = "needs_reply"

    def deltas(self, ctx: DecisionContext) -> dict[str, float]:
        if ctx.needs_reply == 0:
            return {"ignore": 40.0}
        return {"ignore": -25.0}


class GreetingIntakeCriterion:
    name = "greeting_intake"

    def deltas(self, ctx: DecisionContext) -> dict[str, float]:
        if is_short_greeting(ctx.incoming_text):
            return {"ignore": 5.0}
        return {}


class LifeIgnoreCriterion:
    name = "life_ignore"

    def deltas(self, ctx: DecisionContext) -> dict[str, float]:
        mapping = {"working": 5.0, "resting": 15.0, "running": 10.0, "public": 15.0}
        delta = mapping.get(ctx.life.activity)
        return {"ignore": delta} if delta is not None else {}


class MoodIgnoreCriterion:
    name = "mood_ignore"

    def deltas(self, ctx: DecisionContext) -> dict[str, float]:
        if ctx.life.mood == "good":
            return {"ignore": -10.0}
        if ctx.life.mood == "bad":
            return {"ignore": 25.0}
        return {}


class OutgoingLengthCriterion:
    name = "outgoing_length"

    def deltas(self, ctx: DecisionContext) -> dict[str, float]:
        if word_count(ctx.outgoing_text) > 15:
            return {"voice": 25.0, "text": -10.0}
        return {}


class MirrorVoiceCriterion:
    name = "mirror_voice"

    def deltas(self, ctx: DecisionContext) -> dict[str, float]:
        if set(ctx.incoming_types) & {"voice", "audio"}:
            return {"voice": 30.0, "text": -10.0}
        return {}


class VoiceStreakCriterion:
    name = "voice_streak"

    def deltas(self, ctx: DecisionContext) -> dict[str, float]:
        n = ctx.chat.consecutive_voice_out
        if n >= 4:
            return {"voice": -40.0, "text": 25.0}
        if n in (1, 2):
            return {"voice": 10.0}
        return {}


class StyleSwitchCriterion:
    name = "style_switch"

    def deltas(self, ctx: DecisionContext) -> dict[str, float]:
        if ctx.chat.last_delivery == "text" and word_count(ctx.outgoing_text) > 15:
            return {"voice": 15.0}
        return {}


class NightVoiceCriterion:
    name = "night_voice"

    def deltas(self, ctx: DecisionContext) -> dict[str, float]:
        if is_night(ctx.now, settings.BEHAVIOR_TIMEZONE):
            return {"voice": 20.0, "text": -10.0}
        return {}


class IncomingLengthCriterion:
    name = "incoming_length"

    def deltas(self, ctx: DecisionContext) -> dict[str, float]:
        if word_count(ctx.incoming_text) > 20:
            return {"voice": 15.0, "text": -5.0}
        return {}


class GreetingDeliveryCriterion:
    name = "greeting_delivery"

    def deltas(self, ctx: DecisionContext) -> dict[str, float]:
        if is_short_greeting(ctx.incoming_text):
            return {"text": 15.0, "voice": -20.0}
        return {}


class LifeDeliveryCriterion:
    name = "life_delivery"

    def deltas(self, ctx: DecisionContext) -> dict[str, float]:
        table = {
            "working": {"text": 25.0, "voice": -15.0},
            "resting": {"voice": 25.0, "text": -10.0},
            "running": {"voice": 40.0, "text": -20.0},
            "public": {"text": 25.0, "voice": -30.0},
        }
        return dict(table.get(ctx.life.activity, {}))


class MoodDeliveryCriterion:
    name = "mood_delivery"

    def deltas(self, ctx: DecisionContext) -> dict[str, float]:
        if ctx.life.mood == "good":
            return {"text": 5.0}
        if ctx.life.mood == "bad":
            return {"text": -10.0, "voice": -10.0}
        return {}


class AskedVoiceCriterion:
    name = "asked_voice"

    def deltas(self, ctx: DecisionContext) -> dict[str, float]:
        if ctx.asked_voice == 1:
            return {"voice": 50.0}
        return {}


class WantSpeakCriterion:
    name = "want_speak"

    def deltas(self, ctx: DecisionContext) -> dict[str, float]:
        if ctx.life.activity in {"resting", "running"}:
            return {"voice": 10.0}
        return {}


class EmotionVoiceCriterion:
    name = "emotion_voice"

    def deltas(self, ctx: DecisionContext) -> dict[str, float]:
        if ctx.emotion == 1:
            return {"voice": 20.0, "text": -5.0}
        return {}
