"""Shared chat entities used by telegram, batching, memory, and llm."""

from __future__ import annotations

import re
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

NEXT_MESSAGE_TAG = "<next_message>"
_NEXT_MESSAGE_RE = re.compile(r"</?next_message\s*>", re.IGNORECASE)


class QuotedMessage(BaseModel):
    message_id: int | None = None
    sender_name: str | None = None
    text: str | None = None


class Message(BaseModel):
    text: str | None = None
    message_type: str = "text"
    direction: str = "incoming"
    reply_to: QuotedMessage | None = None
    forward_from: QuotedMessage | None = None
    telegram_message_id: int | None = None


def _quoted_label(kind: str, quoted: QuotedMessage | None) -> str:
    if quoted is None:
        return ""
    who = quoted.sender_name or "someone"
    snippet = (quoted.text or "").strip()
    if snippet:
        return f'[{kind} {who}: "{snippet}"]'
    return f"[{kind} {who}]"


def display_text(msg: Message | dict | str) -> str:
    """User-visible line for LLM context. Reply/forward are markup, not chat style to copy."""
    if isinstance(msg, str):
        return msg
    if isinstance(msg, dict):
        msg = Message.model_validate(msg)
    body = (msg.text or "").strip()
    prefixes: list[str] = []
    if msg.reply_to is not None:
        prefixes.append(_quoted_label("reply to", msg.reply_to))
    if msg.forward_from is not None:
        prefixes.append(_quoted_label("forwarded from", msg.forward_from))
    if not prefixes:
        return body
    return (" ".join(prefixes) + (" " + body if body else "")).strip()


def message_texts(messages: list) -> list[str]:
    return [display_text(msg) for msg in messages]


class Batch(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    telegram_chat_id: int
    telegram_account_id: UUID | None = None
    messages: list[Message] = Field(default_factory=list)


def split_agent_text(content: str) -> list[str]:
    """Split an LLM reply on <next_message> into separate chat bubbles."""
    if not content or not content.strip():
        return []
    normalized = _NEXT_MESSAGE_RE.sub(NEXT_MESSAGE_TAG, content)
    return [part.strip() for part in normalized.split(NEXT_MESSAGE_TAG) if part.strip()]


def outgoing_batch(
    *,
    telegram_chat_id: int,
    telegram_account_id: UUID | None,
    text: str,
) -> Batch:
    return Batch(
        telegram_chat_id=telegram_chat_id,
        telegram_account_id=telegram_account_id,
        messages=[
            Message(text=part, direction="outgoing", message_type="text")
            for part in split_agent_text(text)
        ],
    )
