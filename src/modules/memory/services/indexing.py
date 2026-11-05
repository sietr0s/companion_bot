"""Shared topic indexing for live conversations and imported references."""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.ai import TopicIntelligence
from src.modules.memory.clustering import (
    TopicBlock,
    normalize_cluster_blocks,
    parse_cluster_json,
    split_closed_open,
)
from src.modules.memory.constants import CLUSTER_RETRIES, TOPIC_EMBED_MAX_CHARS
from src.modules.memory.formatting import numbered_window, topic_embed_text
from src.modules.memory.models import Message
from src.modules.memory.repository import VectorRecordRepository

logger = logging.getLogger(__name__)


async def cluster_window(
    llm: TopicIntelligence,
    window: list[Message],
    *,
    hard_cap: bool,
    retries: int = CLUSTER_RETRIES,
) -> list[TopicBlock] | None:
    seqs = [message.sequence_number for message in window]
    numbered = numbered_window(window)
    for attempt in range(1, retries + 1):
        blocks = parse_cluster_json(await llm.cluster_topics(numbered))
        if blocks is not None:
            blocks = normalize_cluster_blocks(blocks, seqs)
        split = split_closed_open(blocks, seqs, hard_cap=hard_cap) if blocks is not None else None
        if split is not None:
            return split[0]
        logger.warning("Invalid topic clusters, attempt %s/%s", attempt, retries)
    return None


class TopicIndexer:
    def __init__(self, llm: TopicIntelligence, vectors: VectorRecordRepository) -> None:
        self._llm = llm
        self._vectors = vectors

    async def store(
        self,
        session: AsyncSession,
        conversation_id: UUID,
        window: list[Message],
        blocks: list[TopicBlock],
        *,
        kind: str,
        partial: bool,
    ) -> int:
        if not blocks:
            return 0
        topics = [block for block in blocks if block.kind == "topic"]
        by_seq = {message.sequence_number: message for message in window}
        texts = [
            topic_embed_text(
                block.topic,
                [(by_seq[seq].direction, by_seq[seq].text) for seq in block.ids],
                max_chars=TOPIC_EMBED_MAX_CHARS,
            )
            for block in topics
        ]
        embeddings = await self._llm.embed(texts, role="document") if texts else []
        # Validate the complete response before writing any records.
        records = [
            {
                "text": block.topic,
                "kind": kind,
                "embedding": embedding,
                "seq_from": block.ids[0],
                "seq_to": block.ids[-1],
                "partial": partial,
            }
            for block, embedding in zip(topics, embeddings, strict=True)
        ]
        await self._vectors.store_indexed_window(
            session, conversation_id, records, max(block.ids[-1] for block in blocks)
        )
        return len(records)
