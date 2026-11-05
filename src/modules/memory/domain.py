"""Memory domain entities and topic-partition rules, independent of storage and transport."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.domain.chat import Batch, Channel, ChatRef
from src.domain.chat import Message as ChatMessage


@dataclass(frozen=True)
class ConversationState:
    id: UUID
    channel: Channel
    chat_id: int
    account_id: UUID | None
    last_sequence_number: int


@dataclass(frozen=True)
class HistoryMessage:
    id: UUID
    conversation_id: UUID
    batch_id: UUID
    text: str
    direction: str
    message_type: str
    sequence_number: int
    created_at: datetime
    updated_at: datetime

    def as_message(self) -> ChatMessage:
        return ChatMessage(text=self.text, direction=self.direction, message_type=self.message_type)


@dataclass(frozen=True)
class HistoryWindow:
    messages: list[HistoryMessage]

    def to_batches(self, chat: ChatRef) -> list[Batch]:
        batches: list[Batch] = []
        for message in self.messages:
            if batches and batches[-1].id == message.batch_id:
                batches[-1].messages.append(message.as_message())
            else:
                batches.append(
                    Batch(
                        id=message.batch_id,
                        channel=chat.channel,
                        chat_id=chat.chat_id,
                        account_id=chat.account_id,
                        conversation_id=chat.conversation_id or message.conversation_id,
                        messages=[message.as_message()],
                    )
                )
        return batches


@dataclass(frozen=True)
class RollingSummary:
    current_summary: str | None
    checkpoint: int
    cluster_checkpoint: int


@dataclass(frozen=True)
class NewMessage:
    text: str
    message_type: str = "text"


@dataclass(frozen=True)
class IndexedTopic:
    conversation_id: UUID
    text: str
    seq_from: int
    seq_to: int
    kind: str = "topic"
    partial: bool = False
    embedding: list[float] | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def title(self) -> str:
        return self.text

    @property
    def message_count(self) -> int:
        return self.seq_to - self.seq_from + 1


@dataclass(frozen=True)
class TopicHistory:
    topic: IndexedTopic
    messages: list[HistoryMessage]


@dataclass(frozen=True)
class TopicBlock:
    topic: str
    ids: list[int]
    kind: str = "topic"


MIN_TOPIC_MESSAGES = 2


def _contiguous_runs(seqs: list[int]) -> list[list[int]]:
    if not seqs:
        return []
    ordered = sorted(set(seqs))
    runs: list[list[int]] = [[ordered[0]]]
    for seq in ordered[1:]:
        if seq == runs[-1][-1] + 1:
            runs[-1].append(seq)
        else:
            runs.append([seq])
    return runs


def normalize_cluster_blocks(
    blocks: list[TopicBlock],
    window_seqs: list[int],
) -> list[TopicBlock] | None:
    """Drop 1-message topics, overlapping noise, and fill leftover ids as noise."""
    if not blocks or not window_seqs:
        return None
    window = set(window_seqs)
    occupied: set[int] = set()
    normalized: list[TopicBlock] = []
    for block in blocks:
        ids = [seq for seq in block.ids if seq in window and seq not in occupied]
        if not ids:
            continue
        kind = block.kind
        if kind == "topic" and len(ids) < MIN_TOPIC_MESSAGES:
            kind = "noise"
        for run in _contiguous_runs(ids):
            run_kind = "noise" if kind == "topic" and len(run) < MIN_TOPIC_MESSAGES else kind
            normalized.append(TopicBlock(block.topic, run, run_kind))
            occupied.update(run)
    leftovers = [seq for seq in window_seqs if seq not in occupied]
    for run in _contiguous_runs(leftovers):
        normalized.append(TopicBlock("noise", run, "noise"))
    if not normalized:
        return None
    order = {seq: i for i, seq in enumerate(window_seqs)}
    normalized.sort(key=lambda block: order.get(block.ids[0], 0))
    return normalized


def split_closed_open(
    blocks: list[TopicBlock],
    window_seqs: list[int],
    *,
    hard_cap: bool,
) -> tuple[list[TopicBlock], list[int]] | None:
    if not blocks or not window_seqs:
        return None
    window = list(window_seqs)
    occupied: set[int] = set()
    for block in blocks:
        if not block.ids:
            return None
        expected = list(range(block.ids[0], block.ids[-1] + 1))
        if block.ids != expected:
            return None
        for seq in block.ids:
            if seq not in window or seq in occupied:
                return None
            occupied.add(seq)
    if occupied != set(window):
        return None
    last = window[-1]
    if hard_cap:
        return list(blocks), []
    closed = [b for b in blocks if last not in b.ids]
    open_blocks = [b for b in blocks if last in b.ids]
    if len(open_blocks) != 1:
        return None
    if open_blocks[0].kind == "noise":
        return list(blocks), []
    return closed, list(open_blocks[0].ids)
