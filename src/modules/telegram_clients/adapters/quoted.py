"""Extract reply / forward metadata from a Telethon message."""

from __future__ import annotations

from typing import Any

from src.domain.chat import QuotedMessage


def _display_name(entity: Any) -> str | None:
    if entity is None:
        return None
    first = getattr(entity, "first_name", None)
    last = getattr(entity, "last_name", None)
    title = getattr(entity, "title", None)
    username = getattr(entity, "username", None)
    parts = " ".join(part for part in (first, last) if isinstance(part, str) and part)
    if parts:
        return parts
    if isinstance(title, str) and title:
        return title
    if isinstance(username, str) and username:
        return username
    return None


def _is_real(value: Any) -> bool:
    return value is not None and type(value).__name__ != "MagicMock"


def extract_forward(msg: Any) -> QuotedMessage | None:
    fwd = getattr(msg, "fwd_from", None)
    if not _is_real(fwd):
        forward = getattr(msg, "forward", None)
        if _is_real(forward):
            fwd = getattr(forward, "original_fwd", None) or forward
        else:
            return None
    if not _is_real(fwd):
        return None

    sender_name = getattr(fwd, "from_name", None)
    if not isinstance(sender_name, str):
        sender_name = None
    if sender_name is None:
        forward = getattr(msg, "forward", None)
        if _is_real(forward):
            sender_name = _display_name(getattr(forward, "sender", None))
            if sender_name is None:
                chat = getattr(forward, "chat", None)
                sender_name = _display_name(chat)

    message_id = getattr(fwd, "channel_post", None)
    if not isinstance(message_id, int):
        message_id = getattr(fwd, "saved_from_msg_id", None)
    if not isinstance(message_id, int):
        message_id = None

    text = getattr(msg, "text", None) or getattr(msg, "message", None)
    if not isinstance(text, str):
        text = None

    if sender_name is None and message_id is None and not text:
        return None
    return QuotedMessage(message_id=message_id, sender_name=sender_name, text=text)


async def extract_reply(msg: Any) -> QuotedMessage | None:
    reply_id = getattr(msg, "reply_to_msg_id", None)
    if not isinstance(reply_id, int):
        reply_to = getattr(msg, "reply_to", None)
        if _is_real(reply_to):
            reply_id = getattr(reply_to, "reply_to_msg_id", None)
    if not isinstance(reply_id, int):
        return None

    getter = getattr(msg, "get_reply_message", None)
    reply = await getter() if callable(getter) else None
    if not _is_real(reply):
        return QuotedMessage(message_id=reply_id)

    sender = None
    get_sender = getattr(reply, "get_sender", None)
    if callable(get_sender):
        sender = await get_sender()
        if not _is_real(sender):
            sender = None

    text = getattr(reply, "text", None) or getattr(reply, "message", None)
    if not isinstance(text, str):
        text = None
    return QuotedMessage(
        message_id=getattr(reply, "id", None) if isinstance(getattr(reply, "id", None), int) else reply_id,
        sender_name=_display_name(sender),
        text=text,
    )


async def quoted_from_telethon(msg: Any) -> tuple[QuotedMessage | None, QuotedMessage | None]:
    return await extract_reply(msg), extract_forward(msg)
