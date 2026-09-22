import pytest

from src.domain.chat import Message
from src.modules.behavior.classifiers import (
    INTAKE_HISTORY_MESSAGES,
    ChatIntakeClassifier,
    format_intake_window,
)


@pytest.mark.asyncio
async def test_classifier_bad_json_fails_open():
    class Bad:
        async def complete(self, system, user, *, preset: str):
            return "Ха, ну ладно, ценю настойчивость!"

    c = ChatIntakeClassifier(Bad(), timeout_s=1)
    assert await c.classify("hi") == (1, 0)


@pytest.mark.asyncio
async def test_classifier_wraps_transcript_and_parses_json():
    seen: list[tuple[str, str, str]] = []

    class Ok:
        async def complete(self, system, user, *, preset: str):
            seen.append((system, user, preset))
            return '{"needs_reply": 0, "asked_voice": 1}'

    c = ChatIntakeClassifier(Ok(), timeout_s=1)
    assert await c.classify("User: hi\nAssistant: hey") == (0, 1)
    system, user, preset = seen[0]
    assert preset == "extract"
    assert "JSON only" in system or "classify" in system.lower()
    assert "do not continue" in user.lower()
    assert "User: hi" in user


def test_format_intake_window_uses_last_ten_user_and_assistant():
    recent = [
        Message(text=f"u{i}", direction="incoming" if i % 2 == 0 else "outgoing") for i in range(14)
    ]
    blob = format_intake_window(recent, [])
    lines = blob.splitlines()
    assert len(lines) == INTAKE_HISTORY_MESSAGES
    assert lines[0] == "User: u4"
    assert lines[-1] == "Assistant: u13"
    assert "u0" not in blob


def test_format_intake_window_falls_back_to_batch():
    blob = format_intake_window([], [Message(text="only batch", direction="incoming")])
    assert blob == "User: only batch"
