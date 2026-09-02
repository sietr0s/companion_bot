"""Glue batch messages and assemble LLM context blocks."""

from __future__ import annotations

from src.domain.chat import message_texts

_LABELS = {
    "incoming": "User",
    "outgoing": "Assistant",
}


def glue_batch(messages: list, direction: str) -> str:
    """direction incoming -> User:, outgoing -> Assistant: each line."""
    label = _LABELS[direction]
    return "\n".join(f"{label}: {msg}" for msg in message_texts(messages))


def numbered_window(messages: list) -> str:
    """ORM messages: sequence_number|User|text."""
    lines = []
    for msg in messages:
        label = _LABELS[msg.direction]
        lines.append(f"{msg.sequence_number}|{label}|{msg.text}")
    return "\n".join(lines)


def format_topic_snippet(topic: str, messages: list[tuple[str, str]]) -> str:
    body = "\n".join(f"{_LABELS[direction]}: {text}" for direction, text in messages)
    return f"{topic}\n{body}" if body else topic


def assemble_context(
    *,
    summary: str | None,
    retrieved: list[str],
    recent: list[tuple[str, str]],
) -> str:
    """recent is (direction, text). Omit empty Summary/Retrieved blocks."""
    parts: list[str] = []
    if summary:
        parts.append(f"Summary: {summary}")
    if retrieved:
        lines = ["Retrieved:"] + [f"- {item}" for item in retrieved]
        parts.append("\n".join(lines))
    if recent:
        parts.append(
            "\n".join(f"{_LABELS[direction]}: {text}" for direction, text in recent)
        )
    return "\n".join(parts)
