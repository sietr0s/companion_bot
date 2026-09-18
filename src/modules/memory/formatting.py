"""Helpers for clustering/embed input. Reply prompts live in llm.formatting."""

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


def retrieve_pre_input(
    recent: list[tuple[str, str]],
    limit: int,
) -> tuple[list[str], str]:
    """Last `limit` turns as User/Assistant lines; fallback is last incoming texts."""
    window = recent[-limit:] if limit > 0 else list(recent)
    lines = [f"{_LABELS[direction]}: {text}" for direction, text in window]
    last_user = [text for direction, text in window if direction == "incoming"]
    fallback = (last_user[-1] if last_user else " ".join(text for _, text in window)).strip()
    return lines, fallback


def numbered_window(messages: list) -> str:
    """ORM messages: sequence_number|User|text."""
    lines = []
    for msg in messages:
        label = _LABELS[msg.direction]
        lines.append(f"{msg.sequence_number}|{label}|{msg.text}")
    return "\n".join(lines)


def format_topic_snippet(
    topic: str,
    messages: list[tuple[str, str]],
    *,
    max_messages: int | None = None,
) -> str:
    truncated = False
    clipped = messages
    if max_messages is not None and max_messages > 0 and len(messages) > max_messages:
        clipped = messages[-max_messages:]
        truncated = True
    body = "\n".join(f"{_LABELS[direction]}: {text}" for direction, text in clipped)
    if truncated:
        body = "…\n" + body
    return f"{topic}\n{body}" if body else topic


def topic_embed_text(
    title: str,
    messages: list[tuple[str, str]],
    *,
    max_chars: int,
) -> str:
    body = "\n".join(f"{_LABELS[direction]}: {text}" for direction, text in messages)
    if max_chars > 0 and len(body) > max_chars:
        body = body[:max_chars].rstrip()
    title = (title or "").strip()
    if not body:
        return title
    if not title:
        return body
    return f"{title}\n{body}"
