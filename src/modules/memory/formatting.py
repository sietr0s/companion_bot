"""Glue batch messages and assemble LLM context blocks."""

from __future__ import annotations

_LABELS = {
    "incoming": "User",
    "outgoing": "Assistant",
}


def glue_batch(messages: list[str], direction: str) -> str:
    """direction incoming -> User:, outgoing -> Assistant: each line."""
    label = _LABELS[direction]
    return "\n".join(f"{label}: {msg}" for msg in messages)


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
