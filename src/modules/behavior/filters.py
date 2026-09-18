"""Hard blockers for delivery actions."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from src.modules.behavior.scoring import word_count

if TYPE_CHECKING:
    from src.modules.behavior.engine import DecisionContext

_DIGITS = re.compile(r"\d{5,}")
_URL = re.compile(r"https?://|t\.me/", re.IGNORECASE)


def voice_block_reason(text: str) -> str | None:
    if _DIGITS.search(text):
        return "digits"
    if _URL.search(text):
        return "url"
    if "```" in text:
        return "markup"
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#") or stripped.startswith("|"):
            return "markup"
    if word_count(text) <= 5:
        return "short"
    return None


class VoiceHardFilter:
    name = "voice_hard"

    def blocked(self, ctx: DecisionContext) -> dict[str, str]:
        reason = voice_block_reason(ctx.outgoing_text)
        if reason:
            return {"voice": reason}
        return {}


class InstagramChannelVoiceFilter:
    name = "instagram_voice"

    def blocked(self, ctx: DecisionContext) -> dict[str, str]:
        if getattr(ctx, "channel", "telegram") == "instagram":
            return {"voice": "instagram"}
        return {}
