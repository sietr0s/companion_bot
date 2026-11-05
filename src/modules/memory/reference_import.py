"""Load a Telegram Desktop JSON export into reference vector memory."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import uuid4

from src.domain.ai import TopicIntelligence
from src.modules.memory.services.indexing import TopicIndexer, cluster_window

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.modules.memory.models import Message

from src.modules.memory.constants import REFERENCE_CLUSTER_WINDOW
from src.modules.memory.repository import (
    ConversationRepository,
    MessageBatchRepository,
    MessageRepository,
    SummaryStateRepository,
    VectorRecordRepository,
)

logger = logging.getLogger(__name__)

_CLUSTER_RETRIES = 3


ClusterLLM = TopicIntelligence


@dataclass(frozen=True)
class ParsedTurn:
    direction: str
    text: str


@dataclass(frozen=True)
class ParsedExport:
    name: str
    peer_id: int
    telegram_chat_id: int
    turns: list[ParsedTurn]


def extract_text(raw: object) -> str:
    if isinstance(raw, str):
        return raw.strip()
    if isinstance(raw, list):
        parts: list[str] = []
        for item in raw:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text") or ""))
        return "".join(parts).strip()
    return ""


def parse_telegram_export(path: Path) -> ParsedExport:
    data = json.loads(path.read_text(encoding="utf-8"))
    peer_id = int(data["id"])
    name = str(data.get("name") or "reference")
    peer_from_id = f"user{peer_id}"
    turns: list[ParsedTurn] = []
    for item in data.get("messages") or []:
        if item.get("type") != "message":
            continue
        text = extract_text(item.get("text"))
        if not text:
            continue
        from_id = str(item.get("from_id") or "")
        direction = "outgoing" if from_id == peer_from_id else "incoming"
        turns.append(ParsedTurn(direction=direction, text=text))
    return ParsedExport(
        name=name,
        peer_id=peer_id,
        telegram_chat_id=-abs(peer_id),
        turns=turns,
    )


async def load_reference_export(
    session: AsyncSession,
    llm: ClusterLLM,
    path: Path,
    *,
    replace: bool = False,
) -> dict[str, int]:
    parsed = parse_telegram_export(path)
    if not parsed.turns:
        raise ValueError(f"no text messages in {path}")

    conversations = ConversationRepository()
    messages = MessageRepository()
    batches = MessageBatchRepository()
    summaries = SummaryStateRepository()
    vectors = VectorRecordRepository()

    conversation = await conversations.get_by_chat_id(
        session, parsed.telegram_chat_id, channel="telegram"
    )
    if conversation is not None and replace:
        await vectors.delete_for_conversation(session, conversation.id)
        await messages.delete_for_conversation(session, conversation.id)
        conversation = await conversations.update(
            session,
            conversation,
            {"last_sequence_number": 0},
        )
        state = await summaries.get_by_conversation_id(session, conversation.id)
        if state is not None:
            await summaries.update(session, state, {"cluster_checkpoint": 0, "checkpoint": 0})

    if conversation is None:
        conversation = await conversations.create(
            session,
            {
                "channel": "telegram",
                "chat_id": parsed.telegram_chat_id,
                "user_id": uuid4(),
            },
        )

    if conversation.last_sequence_number == 0:
        first = await conversations.allocate_sequence_numbers(
            session, conversation.id, len(parsed.turns)
        )
        current_dir = None
        batch_id = None
        for offset, turn in enumerate(parsed.turns):
            if current_dir != turn.direction:
                batch = await batches.create(
                    session,
                    {
                        "conversation_id": conversation.id,
                        "direction": turn.direction,
                    },
                )
                batch_id = batch.id
                current_dir = turn.direction
            await messages.create(
                session,
                {
                    "conversation_id": conversation.id,
                    "batch_id": batch_id,
                    "text": turn.text,
                    "direction": turn.direction,
                    "message_type": "text",
                    "sequence_number": first + offset,
                },
            )
        await session.flush()
        logger.info("inserted %s reference messages for %s", len(parsed.turns), parsed.name)

    topics_written = 0
    while True:
        state = await summaries.get_by_conversation_id(session, conversation.id)
        checkpoint = state.cluster_checkpoint if state else 0
        window = await messages.get_after_checkpoint(session, conversation.id, checkpoint)
        if not window:
            break
        slice_ = window[:REFERENCE_CLUSTER_WINDOW]
        closed = await _cluster_window(llm, slice_)
        if closed is None:
            skipped_to = slice_[-1].sequence_number
            logger.warning(
                "cluster failed at checkpoint=%s window=%s; skipping to %s",
                checkpoint,
                len(slice_),
                skipped_to,
            )
            await summaries.upsert_cluster_checkpoint(session, conversation.id, skipped_to)
            await session.commit()
            if skipped_to <= checkpoint:
                break
            continue
        count = await TopicIndexer(llm, vectors).store(
            session, conversation.id, slice_, closed, kind="reference", partial=False
        )
        topics_written += count
        max_closed = max((block.ids[-1] for block in closed), default=checkpoint)
        logger.info("reference topics +%s checkpoint=%s", count, max_closed)
        if max_closed <= checkpoint:
            break

    return {
        "messages": len(parsed.turns),
        "topics": topics_written,
        "chat_id": parsed.telegram_chat_id,
    }


async def _cluster_window(llm: ClusterLLM, window: list[Message]):
    return await cluster_window(llm, window, hard_cap=True, retries=_CLUSTER_RETRIES)
