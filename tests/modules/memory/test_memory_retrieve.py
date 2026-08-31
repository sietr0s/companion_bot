import uuid

import pytest
from sqlalchemy import func, select

from src.bus.in_memory.producer import InMemoryProducer
from src.bus.in_memory.transport import InMemoryTransport
from src.modules.memory.constants import EMBEDDING_DIM
from src.modules.memory.models import VectorRecord
from src.modules.memory.repository import (
    ConversationRepository,
    MessageRepository,
    SummaryStateRepository,
    VectorRecordRepository,
)
from src.modules.memory.schemas.events import ProcessBatchCommand
from src.modules.memory.service import MemoryService


class RecordingLLM:
    def __init__(self):
        self.embed_calls = []
        self.summarize_calls = []

    async def embed(self, texts, *, role):
        self.embed_calls.append((texts, role))
        return [[0.5] * EMBEDDING_DIM for _ in texts]

    async def retrieve_pre(self, batch_messages):
        return "query"

    async def retrieve_post(self, query, hits):
        return hits

    async def summarize(self, current_summary, messages, max_chars=1000):
        self.summarize_calls.append(messages)
        return "SUM"


def _service(llm) -> MemoryService:
    return MemoryService(
        conversations=ConversationRepository(),
        messages=MessageRepository(),
        summaries=SummaryStateRepository(),
        vectors=VectorRecordRepository(),
        message_bus=InMemoryProducer(InMemoryTransport()),
        llm=llm,
    )


@pytest.mark.asyncio
async def test_process_batch_writes_one_vector(db_session):
    llm = RecordingLLM()
    svc = _service(llm)
    cmd = ProcessBatchCommand(
        telegram_chat_id=10, messages=["hello", "world"], batch_id=uuid.uuid4()
    )
    event = await svc.process_batch(db_session, cmd)
    assert event.messages == ["hello", "world"]
    rows = (await db_session.execute(select(VectorRecord))).scalars().all()
    assert len(rows) == 1
    assert "User: hello" in rows[0].text
    assert rows[0].extra_data["seq_from"] == 1
    assert rows[0].extra_data["seq_to"] == 2
    assert llm.embed_calls[0][1] == "document"
    assert llm.summarize_calls == []


@pytest.mark.asyncio
async def test_process_batch_summarizes_when_threshold_met(db_session):
    conv_repo = ConversationRepository()
    conv = await conv_repo.create(
        db_session,
        {
            "telegram_chat_id": 11,
            "user_id": uuid.uuid4(),
            "last_sequence_number": 49,
        },
    )
    summaries = SummaryStateRepository()
    await summaries.create(
        db_session,
        {"conversation_id": conv.id, "current_summary": None, "checkpoint": 0},
    )
    llm = RecordingLLM()
    svc = _service(llm)
    cmd = ProcessBatchCommand(
        telegram_chat_id=11, messages=["fifty"], batch_id=uuid.uuid4()
    )
    await svc.process_batch(db_session, cmd)
    summary = await summaries.get_by_conversation_id(db_session, conv.id)
    assert summary.current_summary == "SUM"
    assert summary.checkpoint == 50


@pytest.mark.asyncio
async def test_process_batch_skips_vector_if_embed_fails(db_session):
    class Boom:
        async def embed(self, texts, *, role):
            raise RuntimeError("gpu")

        async def summarize(self, current_summary, messages, max_chars=1000):
            return "x"

    svc = _service(Boom())
    cmd = ProcessBatchCommand(
        telegram_chat_id=12, messages=["hello"], batch_id=uuid.uuid4()
    )
    event = await svc.process_batch(db_session, cmd)
    assert event.sequence_numbers
    count = (
        await db_session.execute(select(func.count()).select_from(VectorRecord))
    ).scalar()
    assert count == 0
