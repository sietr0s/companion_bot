"""Intake JSON classifier."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import TYPE_CHECKING, Protocol

from src.domain.chat import Batch, Message, display_text
from src.utils.prompt_loader import load_prompt

if TYPE_CHECKING:
    from src.modules.llm.providers.base import ChatProvider

_INTAKE_PROMPT = load_prompt("intake")
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)
INTAKE_HISTORY_MESSAGES = 10
_ROLE = {"incoming": "User", "outgoing": "Assistant"}
logger = logging.getLogger(__name__)


def _classification_payload(window: str) -> str:
    return f"Transcript (do not continue this chat; output JSON only):\n{window.strip()}\nJSON:"


def format_intake_window(
    recent: list[Message],
    batch: Batch,
    *,
    limit: int = INTAKE_HISTORY_MESSAGES,
) -> str:
    """Last `limit` User+Assistant turns for needs_reply classification."""
    turns: list[tuple[str, str]] = []
    for msg in recent:
        text = display_text(msg)
        if text:
            turns.append((msg.direction or "incoming", text))
    if not turns:
        msgs = batch.messages if hasattr(batch, "messages") else batch
        for msg in msgs:
            text = display_text(msg)
            if text:
                turns.append((msg.direction or "incoming", text))
    window = turns[-limit:] if limit > 0 else turns
    return "\n".join(f"{_ROLE.get(direction, direction)}: {text}" for direction, text in window)


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
                self._chat.complete(
                    _INTAKE_PROMPT, _classification_payload(user_text), preset="extract"
                ),
                timeout=self._timeout_s,
            )
        except TimeoutError:
            logger.warning("intake classify timed out after %ss, fail-open", self._timeout_s)
            return 1, 0
        except Exception:
            logger.exception("intake classify failed, fail-open")
            return 1, 0
        parsed = _parse_flags(raw)
        if parsed is None:
            logger.warning("invalid intake JSON, fail-open needs_reply=1: %r", raw)
            return 1, 0
        return parsed
