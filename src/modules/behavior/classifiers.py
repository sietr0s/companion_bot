"""Intake JSON classifier."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Protocol

from src.modules.llm.providers.base import ChatProvider

logger = logging.getLogger(__name__)

_INTAKE_PROMPT = (Path(__file__).resolve().parent / "prompts" / "intake.md").read_text(
    encoding="utf-8"
).strip()
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


class IntakeClassifier(Protocol):
    async def classify(self, user_text: str) -> tuple[int, int]: ...


class FakeIntakeClassifier:
    def __init__(self, needs_reply: int = 1, asked_voice: int = 0) -> None:
        self.needs_reply = needs_reply
        self.asked_voice = asked_voice

    async def classify(self, user_text: str) -> tuple[int, int]:
        return self.needs_reply, self.asked_voice


def _parse_flags(raw: str) -> tuple[int, int] | None:
    match = _JSON_RE.search(raw or "")
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    try:
        needs = int(data.get("needs_reply", 1))
        asked = int(data.get("asked_voice", 0))
    except (TypeError, ValueError):
        return None
    if needs not in (0, 1) or asked not in (0, 1):
        return None
    return needs, asked


class ChatIntakeClassifier:
    def __init__(self, chat: ChatProvider, timeout_s: float) -> None:
        self._chat = chat
        self._timeout_s = timeout_s

    async def classify(self, user_text: str) -> tuple[int, int]:
        try:
            raw = await asyncio.wait_for(
                self._chat.complete(_INTAKE_PROMPT, user_text),
                timeout=self._timeout_s,
            )
        except Exception:
            logger.exception("intake classify failed")
            return 1, 0
        parsed = _parse_flags(raw)
        if parsed is None:
            return 1, 0
        return parsed
