"""Shared chat entities used by telegram, batching, memory, and llm."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, Literal
from uuid import UUID, uuid4

Channel = Literal["telegram", "instagram"]

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

NEXT_MESSAGE_TAG = "<next_message>"
_NEXT_MESSAGE_RE = re.compile(r"</?next_message\s*>", re.IGNORECASE)


class ChatRef(BaseModel):
    """Identity of a companion chat on one channel."""

    channel: Channel
    chat_id: int
    account_id: UUID | None = None
    conversation_id: UUID | None = None

    def state_key(self) -> tuple[str, str, int]:
        return (
            self.channel,
            str(self.account_id) if self.account_id else "",
            int(self.chat_id),
        )

    def bus_ids(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "account_id": str(self.account_id) if self.account_id else None,
            "chat_id": self.chat_id,
            "conversation_id": str(self.conversation_id) if self.conversation_id else None,
        }

    def adapter_ids(self) -> dict[str, Any]:
        return {
            "account_id": str(self.account_id) if self.account_id else None,
            "chat_id": self.chat_id,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> ChatRef:
        channel = payload.get("channel")
        if channel not in ("telegram", "instagram"):
            raise ValueError("payload has no valid channel")
        chat_id = payload.get("chat_id")
        if chat_id is None:
            raise ValueError("payload has no chat_id")
        account = payload.get("account_id")
        conv = payload.get("conversation_id")
        return cls(
            channel=channel,
            chat_id=int(chat_id),
            account_id=UUID(str(account)) if account else None,
            conversation_id=UUID(str(conv)) if conv else None,
        )

    def merged(self, other: ChatRef) -> ChatRef:
        return ChatRef(
            channel=other.channel or self.channel,
            chat_id=other.chat_id or self.chat_id,
            account_id=other.account_id or self.account_id,
            conversation_id=other.conversation_id or self.conversation_id,
        )


class Person(BaseModel):
    sender_id: int | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None

    @property
    def display_name(self) -> str | None:
        parts = " ".join(p for p in (self.first_name, self.last_name) if p).strip()
        return parts or self.username


class QuotedMessage(BaseModel):
    message_id: int | None = None
    sender_name: str | None = None
    text: str | None = None


class Message(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    text: str | None = None
    message_type: str = "text"
    direction: str = "incoming"
    reply_to: QuotedMessage | None = None
    forward_from: QuotedMessage | None = None
    message_id: str | int | None = Field(
        default=None,
        validation_alias=AliasChoices("message_id", "telegram_message_id"),
    )


class Batch(ChatRef):
    """Same-role bubbles written together."""

    id: UUID = Field(default_factory=uuid4)
    messages: list[Message] = Field(default_factory=list)

    @property
    def direction(self) -> str:
        return self.messages[0].direction if self.messages else "incoming"


class Topic(BaseModel):
    """Vector hit: title plus batches in seq range."""

    title: str
    kind: str = "topic"
    conversation_id: UUID | None = None
    seq_from: int | None = None
    seq_to: int | None = None
    batches: list[Batch] = Field(default_factory=list)


class ConversationContext(BaseModel):
    """Memory for a reply. Prompt text is built in the LLM module."""

    summary: str | None = None
    retrieved: list[Topic] = Field(default_factory=list)
    references: list[Topic] = Field(default_factory=list)
    recent: list[Batch] = Field(default_factory=list)

    def recent_messages(self) -> list[Message]:
        return [msg for batch in self.recent for msg in batch.messages]

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> ConversationContext:
        nested = payload.get("memory")
        if isinstance(nested, ConversationContext):
            return nested
        if isinstance(nested, Mapping):
            return cls.model_validate(nested)
        return cls.model_validate(
            {
                "summary": payload.get("summary"),
                "retrieved": payload.get("retrieved") or [],
                "references": payload.get("references") or [],
                "recent": payload.get("recent") or [],
            }
        )


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


def split_agent_text(content: str) -> list[str]:
    """Split an LLM reply on <next_message> into separate chat bubbles."""
    if not content or not content.strip():
        return []
    normalized = _NEXT_MESSAGE_RE.sub(NEXT_MESSAGE_TAG, content)
    return [part.strip() for part in normalized.split(NEXT_MESSAGE_TAG) if part.strip()]


def outgoing_batch(
    *,
    channel: Channel,
    chat_id: int,
    account_id: UUID | None,
    text: str,
) -> Batch:
    return Batch(
        channel=channel,
        chat_id=chat_id,
        account_id=account_id,
        messages=[
            Message(text=part, direction="outgoing", message_type="text")
            for part in split_agent_text(text)
        ],
    )
