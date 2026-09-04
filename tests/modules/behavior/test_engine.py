import random
from datetime import UTC, datetime

from src.modules.behavior.engine import (
    DecisionContext,
    LifeSnapshot,
    Policy,
    decide,
    softmax_sample,
)
from src.modules.behavior.filters import VoiceHardFilter
from src.modules.behavior.policies import DELIVERY_POLICY, INTAKE_POLICY


class BoostSticker:
    name = "boost_sticker"

    def deltas(self, ctx):
        return {"sticker": 100.0, "text": -5.0}


def test_new_action_is_opt_in_via_legal_actions():
    rng = random.Random(0)
    ctx = DecisionContext(now=datetime.now(UTC))
    policy = Policy(
        name="t",
        legal_actions=("text", "sticker"),
        base_weights={"text": 10, "sticker": 0},
        criteria=(BoostSticker(),),
        filters=(),
        fallback="text",
    )
    d = decide(policy, ctx, rng)
    assert d.action == "sticker"
    assert "sticker" in d.scores


def test_unknown_delta_keys_are_dropped():
    rng = random.Random(0)
    policy = Policy(
        name="t",
        legal_actions=("text",),
        base_weights={"text": 10},
        criteria=(BoostSticker(),),
        filters=(),
        fallback="text",
    )
    d = decide(policy, DecisionContext(), rng)
    assert "sticker" not in d.scores
    assert d.action == "text"


def test_softmax_all_zero_fallback():
    rng = random.Random(0)
    assert softmax_sample({"text": 0, "voice": 0}, rng, fallback="text") == "text"


def test_voice_hard_filter_blocks_digits():
    ctx = DecisionContext(outgoing_text="call 89001234567 extra words here")
    blocked = VoiceHardFilter().blocked(ctx)
    assert blocked.get("voice")


def test_delivery_policy_cannot_pick_voice_when_blocked():
    rng = random.Random(0)
    ctx = DecisionContext(
        outgoing_text="https://t.me/x and more words in this reply",
        asked_voice=1,
        emotion=1,
        life=LifeSnapshot("resting", "good"),
        now=datetime(2026, 1, 1, 23, tzinfo=UTC),
    )
    for _ in range(20):
        assert decide(DELIVERY_POLICY, ctx, rng).action != "voice"


def test_intake_needs_reply_zero_raises_ignore_score():
    rng = random.Random(0)
    life = LifeSnapshot("working", "neutral")
    now = datetime(2026, 1, 1, 12, tzinfo=UTC)
    a = decide(
        INTAKE_POLICY,
        DecisionContext(incoming_text="long message here", life=life, needs_reply=0, now=now),
        rng,
    )
    b = decide(
        INTAKE_POLICY,
        DecisionContext(incoming_text="long message here", life=life, needs_reply=1, now=now),
        rng,
    )
    assert a.scores["ignore"] > b.scores["ignore"]
