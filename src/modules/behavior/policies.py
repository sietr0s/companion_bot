"""v1 intake and delivery policies."""

from src.modules.behavior.criteria import (
    AskedVoiceCriterion,
    EmotionVoiceCriterion,
    GreetingDeliveryCriterion,
    GreetingIntakeCriterion,
    IncomingLengthCriterion,
    LifeDeliveryCriterion,
    LifeIgnoreCriterion,
    MirrorVoiceCriterion,
    MoodDeliveryCriterion,
    MoodIgnoreCriterion,
    NeedsReplyCriterion,
    NightVoiceCriterion,
    OutgoingLengthCriterion,
    StyleSwitchCriterion,
    VoiceStreakCriterion,
    WantSpeakCriterion,
)
from src.modules.behavior.engine import Policy
from src.modules.behavior.filters import VoiceHardFilter

INTAKE_POLICY = Policy(
    name="intake",
    legal_actions=("ignore", "respond"),
    base_weights={"respond": 50.0, "ignore": 10.0},
    criteria=(
        NeedsReplyCriterion(),
        GreetingIntakeCriterion(),
        LifeIgnoreCriterion(),
        MoodIgnoreCriterion(),
    ),
    filters=(),
    fallback="respond",
)

DELIVERY_POLICY = Policy(
    name="delivery",
    legal_actions=("text", "voice"),
    base_weights={"text": 40.0, "voice": 20.0},
    criteria=(
        OutgoingLengthCriterion(),
        MirrorVoiceCriterion(),
        VoiceStreakCriterion(),
        StyleSwitchCriterion(),
        NightVoiceCriterion(),
        IncomingLengthCriterion(),
        GreetingDeliveryCriterion(),
        LifeDeliveryCriterion(),
        MoodDeliveryCriterion(),
        AskedVoiceCriterion(),
        WantSpeakCriterion(),
        EmotionVoiceCriterion(),
    ),
    filters=(VoiceHardFilter(),),
    fallback="text",
)
