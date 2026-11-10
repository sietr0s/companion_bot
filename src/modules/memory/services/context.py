"""Build recent and retrieved context, independent of bus delivery."""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.ai import MemoryIntelligence
from src.domain.chat import ChatRef, ConversationContext, Topic
from src.modules.memory.config import get_settings
from src.modules.memory.domain import HistoryWindow
from src.modules.memory.repository import (
    ConversationRepository,
    MessageRepository,
    SummaryStateRepository,
    VectorRecordRepository,
)
from src.modules.memory.utils import (
    retrieve_pre_input,
)

logger = logging.getLogger(__name__)


class ContextBuilder:
    def __init__(
        self,
        conversations: ConversationRepository,
        messages: MessageRepository,
        summaries: SummaryStateRepository,
        vectors: VectorRecordRepository,
        llm: MemoryIntelligence,
    ) -> None:
        self._conversations = conversations
        self._messages = messages
        self._summaries = summaries
        self._vectors = vectors
        self._llm = llm

    async def _retrieve_snippets(
        self,
        session: AsyncSession,
        *,
        query: str,
        query_embedding: list[float],
        conversation_id: UUID | None,
        kind: str,
        recent_min_seq: int | None = None,
        chat: ChatRef,
    ) -> list[Topic]:
        hits = await self._vectors.search_similar(
            session,
            conversation_id,
            query_embedding,
            get_settings().VECTOR_TOP_K,
            kind=kind,
        )
        ranked = await self._llm.retrieve_post(query, [h.text for h in hits])
        unused = list(hits)
        topics: list[Topic] = []
        for title in ranked:
            hit = None
            for index, candidate in enumerate(unused):
                if candidate.text == title:
                    hit = unused.pop(index)
                    break
            if hit is None:
                continue
            seq_from, seq_to = hit.seq_from, hit.seq_to
            if recent_min_seq is not None and seq_from >= recent_min_seq:
                continue
            if recent_min_seq is not None:
                seq_to = min(seq_to, recent_min_seq - 1)
            if seq_to < seq_from:
                continue
            msgs = await self._messages.get_between_inclusive(
                session, hit.conversation_id, seq_from, seq_to
            )
            if (
                get_settings().SNIPPET_MAX_MESSAGES > 0
                and len(msgs) > get_settings().SNIPPET_MAX_MESSAGES
            ):
                msgs = msgs[-get_settings().SNIPPET_MAX_MESSAGES :]
            conv = await self._conversations.get_state(session, hit.conversation_id)
            topic_chat = ChatRef(
                channel=chat.channel,
                chat_id=conv.chat_id if conv else chat.chat_id,
                account_id=conv.account_id if conv else chat.account_id,
                conversation_id=hit.conversation_id,
            )
            topics.append(
                Topic(
                    title=title,
                    kind=hit.kind,
                    conversation_id=hit.conversation_id,
                    seq_from=seq_from,
                    seq_to=seq_to,
                    batches=HistoryWindow(msgs).to_batches(topic_chat),
                )
            )
        return topics

    async def build_context(
        self, session: AsyncSession, chat: ChatRef, last_n_messages: int
    ) -> ConversationContext:
        conversation_id = chat.conversation_id
        if conversation_id is None:
            raise ValueError("A conversation is required to build memory context")
        messages = await self._messages.get_last_messages(
            session, conversation_id, limit=last_n_messages
        )
        summary_state = await self._summaries.get_by_conversation_id(session, conversation_id)
        summary = summary_state.current_summary if summary_state else None
        recent_batches = HistoryWindow(messages).to_batches(chat)
        recent_pairs = [(msg.direction, msg.text) for msg in messages]

        retrieved: list[Topic] = []
        references: list[Topic] = []
        recent_min_seq = messages[0].sequence_number if messages else None
        try:
            pre_lines, pre_fallback = retrieve_pre_input(
                recent_pairs, get_settings().RETRIEVE_PRE_WINDOW
            )
            query = await self._llm.retrieve_pre(pre_lines, fallback=pre_fallback)
            qvec = (await self._llm.embed([query], role="query"))[0]
            retrieved = await self._retrieve_snippets(
                session,
                query=query,
                query_embedding=qvec,
                conversation_id=conversation_id,
                kind="topic",
                recent_min_seq=recent_min_seq,
                chat=chat,
            )
            references = await self._retrieve_snippets(
                session,
                query=query,
                query_embedding=qvec,
                conversation_id=None,
                kind="reference",
                chat=chat,
            )
        except Exception:
            logger.exception("retrieve failed")
            retrieved = []
            references = []

        return ConversationContext(
            summary=summary, retrieved=retrieved, references=references, recent=recent_batches
        )
