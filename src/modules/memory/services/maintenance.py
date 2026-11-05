"""Serialize per-conversation clustering and rolling summaries."""

import asyncio
import logging
from uuid import UUID
from weakref import WeakValueDictionary

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.ai import MemoryIntelligence
from src.modules.memory.constants import (
    CLUSTER_HARD_CAP,
    CLUSTER_MIN_MESSAGES,
    SUMMARY_THRESHOLD,
)
from src.modules.memory.repository import (
    MessageRepository,
    SummaryStateRepository,
    VectorRecordRepository,
)
from src.modules.memory.services.indexing import TopicIndexer, cluster_window

logger = logging.getLogger(__name__)


class MemoryMaintenance:
    def __init__(
        self,
        messages: MessageRepository,
        summaries: SummaryStateRepository,
        vectors: VectorRecordRepository,
        llm: MemoryIntelligence,
    ) -> None:
        self._messages = messages
        self._summaries = summaries
        self._vectors = vectors
        self._llm = llm
        self._maintain_locks: WeakValueDictionary[UUID, asyncio.Lock] = WeakValueDictionary()
        self._indexer = TopicIndexer(llm, vectors)

    async def _maybe_cluster(
        self,
        session: AsyncSession,
        *,
        conversation_id: UUID,
    ) -> None:
        summary_state = await self._summaries.get_by_conversation_id(session, conversation_id)
        checkpoint = summary_state.cluster_checkpoint if summary_state else 0
        window = await self._messages.get_after_checkpoint(session, conversation_id, checkpoint)
        if len(window) < CLUSTER_MIN_MESSAGES:
            return
        hard_cap = len(window) >= CLUSTER_HARD_CAP
        if hard_cap:
            window = window[:CLUSTER_HARD_CAP]
        try:
            closed = await cluster_window(self._llm, window, hard_cap=hard_cap)
            if closed is not None:
                await self._indexer.store(
                    session, conversation_id, window, closed, kind="topic", partial=hard_cap
                )
        except Exception:
            logger.exception("failed to cluster topics")

    async def _maybe_summarize(
        self,
        session: AsyncSession,
        *,
        conversation_id: UUID,
        current_sequence: int,
    ) -> bool:
        summary_state = await self._summaries.get_by_conversation_id(session, conversation_id)
        checkpoint = summary_state.checkpoint if summary_state else 0
        current_summary = summary_state.current_summary if summary_state else None
        if current_sequence - checkpoint < SUMMARY_THRESHOLD:
            return False
        try:
            after = await self._messages.get_between_inclusive(
                session, conversation_id, checkpoint + 1, current_sequence
            )
            new_summary = await self._llm.summarize(current_summary, [m.text for m in after])
            await self._summaries.upsert(
                session,
                conversation_id,
                new_summary,
                current_sequence,
            )
            return True
        except Exception:
            logger.exception("failed to summarize conversation")
            return False

    def _maintain_lock(self, conversation_id: UUID) -> asyncio.Lock:
        lock = self._maintain_locks.get(conversation_id)
        if lock is None:
            lock = asyncio.Lock()
            self._maintain_locks[conversation_id] = lock
        return lock

    async def maintain_memory(
        self, session: AsyncSession, conversation_id: UUID, current_sequence: int
    ) -> None:
        async with self._maintain_lock(conversation_id):
            await self._maybe_cluster(session, conversation_id=conversation_id)
            if current_sequence:
                await self._maybe_summarize(
                    session,
                    conversation_id=conversation_id,
                    current_sequence=current_sequence,
                )
