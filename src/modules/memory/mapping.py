"""ORM rows → domain Batch / Topic. No prompt text."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.domain.chat import Batch, ChatRef, Message, Topic

if TYPE_CHECKING:
    from uuid import UUID


def to_domain_message(row) -> Message:
    return Message(
        text=row.text,
        direction=row.direction,
        message_type=getattr(row, "message_type", None) or "text",
    )


def to_domain_batches(rows: list, chat: ChatRef) -> list[Batch]:
    batches: list[Batch] = []
    for row in rows:
        msg = to_domain_message(row)
        batch_id: UUID = row.batch_id
        if batches and batches[-1].id == batch_id:
            batches[-1].messages.append(msg)
        else:
            batches.append(
                Batch(
                    id=batch_id,
                    channel=chat.channel,
                    chat_id=chat.chat_id,
                    account_id=chat.account_id,
                    conversation_id=chat.conversation_id or getattr(row, "conversation_id", None),
                    messages=[msg],
                )
            )
    return batches


def to_topic(
    *, title: str, kind: str, conversation_id, seq_from: int, seq_to: int, batches: list[Batch]
) -> Topic:
    return Topic(
        title=title,
        kind=kind,
        conversation_id=conversation_id,
        seq_from=seq_from,
        seq_to=seq_to,
        batches=batches,
    )
