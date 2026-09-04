"""Text helpers for behavior scoring."""

from __future__ import annotations

import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

GREETINGS = frozenset({"привет", "здарова", "хай", "йо"})
_EMOTICON_RE = re.compile(r"[:;]-?[)D(]|[\U0001F300-\U0001FAFF]")


def word_count(text: str) -> int:
    return len(text.split())


def first_token(text: str) -> str:
    parts = text.strip().split()
    return parts[0].lower() if parts else ""


def is_short_greeting(text: str) -> bool:
    return word_count(text) <= 3 and first_token(text) in GREETINGS


def local_hour(now: datetime, tz_name: str) -> int:
    return now.astimezone(ZoneInfo(tz_name)).hour


def is_night(now: datetime | None, tz_name: str) -> bool:
    if now is None:
        return False
    return local_hour(now, tz_name) in {22, 23, 0, 1, 2, 3, 4, 5}


def strip_emotion_suffix(text: str) -> tuple[str, int | None]:
    lines = text.splitlines()
    idx = len(lines) - 1
    while idx >= 0 and not lines[idx].strip():
        idx -= 1
    if idx < 0:
        return text.strip(), None
    raw = lines[idx].strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return text.strip(), None
    if not isinstance(data, dict) or "emotion" not in data:
        return text.strip(), None
    try:
        emotion = int(data["emotion"])
    except (TypeError, ValueError):
        return text.strip(), None
    if emotion not in (0, 1):
        return text.strip(), None
    body = "\n".join(lines[:idx]).strip()
    return body, emotion


def detect_emotion(text: str, llm_emotion: int | None = None) -> int:
    if "!" in text or _EMOTICON_RE.search(text):
        return 1
    if llm_emotion in (0, 1):
        return llm_emotion
    return 0
