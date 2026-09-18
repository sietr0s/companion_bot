import json
import uuid

import pytest
from sqlalchemy import func, select

from src.bus.in_memory.producer import InMemoryProducer
from src.bus.in_memory.transport import InMemoryTransport
from src.domain.chat import Batch
from src.modules.memory.constants import EMBEDDING_DIM
from src.modules.memory.models import Conversation, Message, VectorRecord
from src.modules.memory.repository import (
    ConversationRepository,
    MessageRepository,
    SummaryStateRepository,
    VectorRecordRepository,
)
from src.modules.memory.schemas.events import (
    BuildContextCommand,
    MaintainMemoryCommand,
    ProcessBatchCommand,
    UpdateMemoryCommand,
)
from src.modules.memory.service import MemoryService
from tests.modules.memory.seed import insert_message


class RecordingLLM:
    def __init__(self):
        self.embed_calls = []
        self.summarize_calls = []
        self.cluster_calls = []

    async def embed(self, texts, *, role):
        self.embed_calls.append((texts, role))
        return [[0.5] * EMBEDDING_DIM for _ in texts]

    async def retrieve_pre(self, batch_messages, fallback=None):
        return "query"

    async def retrieve_post(self, query, hits):
        return hits

    async def cluster_topics(self, numbered: str) -> str:
        self.cluster_calls.append(numbered)
        return "[]"

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


def _cmd(*, chat_id, messages, account_id=None, batch_id=None):
    return ProcessBatchCommand(
        batch=Batch(
            id=batch_id or uuid.uuid4(),
            channel="telegram",
            chat_id=chat_id,
            account_id=account_id,
            messages=list(messages),
        ),
    )


async def _last_sequence(db_session, conversation_id) -> int:
    row = (
        await db_session.execute(select(Conversation).where(Conversation.id == conversation_id))
    ).scalar_one()
    return row.last_sequence_number


@pytest.mark.asyncio
async def test_process_batch_does_not_index_small_window(db_session):
    llm = RecordingLLM()
    svc = _service(llm)
    cmd = _cmd(
        chat_id=10,
        messages=[{"text": "hello"}, {"text": "world"}],
    )
    event = await svc.process_batch(db_session, cmd)
    rows = (
        await db_session.execute(
            select(Message)
            .where(Message.conversation_id == event.conversation_id)
            .order_by(Message.sequence_number)
        )
    ).scalars().all()
    assert [row.text for row in rows] == ["hello", "world"]
    assert (await db_session.execute(select(VectorRecord))).scalars().all() == []
    assert llm.cluster_calls == []
    assert llm.embed_calls == []


@pytest.mark.asyncio
async def test_process_batch_persists_reply_markup(db_session):
    llm = RecordingLLM()
    svc = _service(llm)
    cmd = _cmd(
        chat_id=13,
        messages=[
            {
                "text": "ок",
                "message_type": "text",
                "reply_to": {"message_id": 10, "sender_name": "Alice", "text": "план"},
            }
        ],
    )
    event = await svc.process_batch(db_session, cmd)
    row = (
        await db_session.execute(
            select(Message).where(Message.conversation_id == event.conversation_id)
        )
    ).scalar_one()
    assert row.text == '[reply to Alice: "план"] ок'
    assert row.message_type == "text"


@pytest.mark.asyncio
async def test_process_batch_summarizes_when_threshold_met(db_session):
    conv_repo = ConversationRepository()
    conv = await conv_repo.create(
        db_session,
        {
            "channel": "telegram",
            "chat_id": 11,
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
    cmd = _cmd(chat_id=11, messages=[{"text": "fifty"}])
    await svc.process_batch(db_session, cmd)
    await svc.maintain_memory(
        db_session,
        MaintainMemoryCommand(
            conversation_id=conv.id,
            channel="telegram",
            chat_id=11,
            current_sequence=50,
        ),
    )
    summary = await summaries.get_by_conversation_id(db_session, conv.id)
    assert summary.current_summary == "SUM"
    assert summary.checkpoint == 50


@pytest.mark.asyncio
async def test_process_batch_skips_vector_if_cluster_fails(db_session):
    class Boom:
        async def cluster_topics(self, numbered: str) -> str:
            raise RuntimeError("gpu")

        async def embed(self, texts, *, role):
            raise RuntimeError("gpu")

        async def summarize(self, current_summary, messages, max_chars=1000):
            return "x"

    svc = _service(Boom())
    cmd = _cmd(
        chat_id=12,
        messages=[{"text": f"m{i}"} for i in range(20)],
    )
    event = await svc.process_batch(db_session, cmd)
    await svc.maintain_memory(
        db_session,
        MaintainMemoryCommand(
            conversation_id=event.conversation_id,
            channel="telegram",
            chat_id=12,
            current_sequence=event.sequence_numbers[-1],
        ),
    )
    assert event.sequence_numbers
    count = (await db_session.execute(select(func.count()).select_from(VectorRecord))).scalar()
    assert count == 0


@pytest.mark.asyncio
async def test_process_batch_indexes_closed_topics(db_session):
    class ClusterLLM(RecordingLLM):
        async def cluster_topics(self, numbered: str) -> str:
            self.cluster_calls.append(numbered)
            seqs = [int(line.split("|", 1)[0]) for line in numbered.splitlines() if line]
            closed = seqs[:5]
            rest = seqs[5:]
            return json.dumps(
                [
                    {"topic": "Приветствие", "ids": closed, "kind": "topic"},
                    {"topic": "Сервер", "ids": rest, "kind": "topic"},
                ]
            )

    llm = ClusterLLM()
    svc = _service(llm)
    cmd = _cmd(
        chat_id=40,
        messages=[{"text": f"m{i}"} for i in range(20)],
    )
    event = await svc.process_batch(db_session, cmd)
    assert llm.cluster_calls == []
    await svc.maintain_memory(
        db_session,
        MaintainMemoryCommand(
            conversation_id=event.conversation_id,
            channel="telegram",
            chat_id=40,
            current_sequence=event.sequence_numbers[-1],
        ),
    )
    rows = (await db_session.execute(select(VectorRecord))).scalars().all()
    assert len(rows) == 1
    assert rows[0].text == "Приветствие"
    assert rows[0].kind == "topic"
    assert llm.embed_calls[0][0][0].startswith("Приветствие")
    assert "User: m0" in llm.embed_calls[0][0][0]
    assert llm.embed_calls[0][1] == "document"
    state = await SummaryStateRepository().get_by_conversation_id(
        db_session, rows[0].conversation_id
    )
    assert state.cluster_checkpoint == 5


def _vec(seed: float) -> list[float]:
    return [seed] * EMBEDDING_DIM


async def _seed_retrieve(db_session, telegram_chat_id: int, vector_rows: list[tuple[str, float]]):
    conv = await ConversationRepository().create(
        db_session,
        {"channel": "telegram", "chat_id": telegram_chat_id, "user_id": uuid.uuid4()},
    )
    await insert_message(db_session, conv.id, text="recent", sequence_number=10)
    await SummaryStateRepository().create(
        db_session,
        {"conversation_id": conv.id, "current_summary": "past", "checkpoint": 0},
    )
    vec_repo = VectorRecordRepository()
    for text, seed in vector_rows:
        await vec_repo.create(
            db_session,
            {
                "conversation_id": conv.id,
                "text": text,
                "embedding": _vec(seed),
                "seq_from": 1,
                "seq_to": 1,
            },
        )
    return conv


def _retrieved_items(context: str) -> list[str]:
    if "Retrieved:" not in context:
        return []
    items = []
    for line in context.split("Retrieved:", 1)[1].splitlines():
        if line.startswith("- "):
            items.append(line[2:])
        elif (
            line.startswith("User:")
            or line.startswith("Assistant:")
            or line.startswith("Reference:")
        ):
            break
    return items


@pytest.mark.asyncio
async def test_build_context_includes_ranked_hits(db_session):
    conv = await _seed_retrieve(db_session, 20, [("old A", 0.9), ("old B", -1.0)])

    class ReversePost(RecordingLLM):
        async def retrieve_post(self, query, hits):
            return list(reversed(hits))

    llm = ReversePost()
    svc = _service(llm)
    event = await svc.build_context(
        db_session,
        BuildContextCommand(
            conversation_id=conv.id,
            channel="telegram",
            chat_id=20,
            batch_messages=[{"text": "now"}],
            last_n_messages=50,
        ),
    )
    assert [t.title for t in event.retrieved] == ["old B", "old A"]
    assert event.retrieved_count == 2
    assert llm.embed_calls[-1][1] == "query"
    assert event.summary == "past"
    assert event.recent[0].messages[0].text == "recent"


@pytest.mark.asyncio
async def test_build_context_retrieves_reference_with_same_query(db_session):
    conv = await _seed_retrieve(db_session, 21, [("old A", 0.9)])
    other = await ConversationRepository().create(
        db_session,
        {"channel": "telegram", "chat_id": 210, "user_id": uuid.uuid4()},
    )
    await VectorRecordRepository().create(
        db_session,
        {
            "conversation_id": other.id,
            "text": "style example",
            "kind": "reference",
            "embedding": _vec(0.9),
            "seq_from": 1,
            "seq_to": 1,
        },
    )
    llm = RecordingLLM()
    svc = _service(llm)
    event = await svc.build_context(
        db_session,
        BuildContextCommand(
            conversation_id=conv.id,
            channel="telegram",
            chat_id=21,
            batch_messages=[{"text": "now"}],
            last_n_messages=50,
        ),
    )
    assert [t.title for t in event.retrieved] == ["old A"]
    assert [t.title for t in event.references] == ["style example"]
    assert [query for query, role in llm.embed_calls if role == "query"]


@pytest.mark.asyncio
async def test_build_context_retrieve_pre_uses_dialogue_window(db_session):
    conv = await ConversationRepository().create(
        db_session,
        {"channel": "telegram", "chat_id": 88, "user_id": uuid.uuid4()},
    )
    await insert_message(db_session, conv.id, text="старое", sequence_number=1)
    await insert_message(
        db_session, conv.id, text="ответила", sequence_number=2, direction="outgoing"
    )
    await insert_message(db_session, conv.id, text="девушка ушла", sequence_number=3)

    class CapturePre(RecordingLLM):
        def __init__(self):
            super().__init__()
            self.pre_arg = None
            self.fallback = None

        async def retrieve_pre(self, batch_messages, fallback=None):
            self.pre_arg = list(batch_messages)
            self.fallback = fallback
            return "query"

    llm = CapturePre()
    svc = _service(llm)
    await svc.build_context(
        db_session,
        BuildContextCommand(
            conversation_id=conv.id,
            channel="telegram",
            chat_id=88,
            batch_messages=[{"text": "девушка ушла"}],
            last_n_messages=50,
        ),
    )
    joined = "\n".join(llm.pre_arg)
    assert "Assistant: ответила" in joined
    assert "User: девушка ушла" in joined
    assert llm.fallback == "девушка ушла"


@pytest.mark.asyncio
async def test_build_context_omits_retrieved_on_pre_failure(db_session):
    conv = await _seed_retrieve(db_session, 22, [("old batch", 0.9)])

    class BoomPre(RecordingLLM):
        async def retrieve_pre(self, batch_messages, fallback=None):
            raise RuntimeError("llm")

    llm = BoomPre()
    svc = _service(llm)
    event = await svc.build_context(
        db_session,
        BuildContextCommand(
            conversation_id=conv.id,
            channel="telegram",
            chat_id=22,
            batch_messages=[{"text": "now"}],
            last_n_messages=50,
        ),
    )
    assert event.retrieved == []
    assert event.retrieved_count == 0
    assert event.recent[0].messages[0].text == "recent"
    assert event.summary == "past"


@pytest.mark.asyncio
async def test_update_memory_does_not_index_small_outgoing(db_session):
    conv = await ConversationRepository().create(
        db_session,
        {"channel": "telegram", "chat_id": 30, "user_id": uuid.uuid4()},
    )
    llm = RecordingLLM()
    svc = _service(llm)
    event = await svc.update_memory(
        db_session,
        UpdateMemoryCommand(
            conversation_id=conv.id,
            channel="telegram",
            chat_id=30,
            outgoing_messages=["reply"],
            delivery_status="delivered",
        ),
    )
    count = (await db_session.execute(select(func.count()).select_from(VectorRecord))).scalar()
    assert count == 0
    assert llm.embed_calls == []
    assert event.summary_updated is False
    assert event.messages_count == 1
    assert llm.summarize_calls == []
    row = (
        await db_session.execute(select(Message).where(Message.conversation_id == conv.id))
    ).scalar_one()
    assert row.message_type == "text"


@pytest.mark.asyncio
async def test_update_memory_stores_voice_type(db_session):
    conv = await ConversationRepository().create(
        db_session,
        {"channel": "telegram", "chat_id": 32, "user_id": uuid.uuid4()},
    )
    svc = _service(RecordingLLM())
    await svc.update_memory(
        db_session,
        UpdateMemoryCommand(
            conversation_id=conv.id,
            channel="telegram",
            chat_id=32,
            outgoing_messages=["hello there friend"],
            delivery_status="delivered",
            message_type="voice",
        ),
    )
    row = (
        await db_session.execute(select(Message).where(Message.conversation_id == conv.id))
    ).scalar_one()
    assert row.message_type == "voice"
    assert row.text == "hello there friend"


@pytest.mark.asyncio
async def test_build_context_hydrates_topic_messages(db_session):
    conv = await ConversationRepository().create(
        db_session,
        {"channel": "telegram", "chat_id": 50, "user_id": uuid.uuid4()},
    )
    await insert_message(db_session, conv.id, text="сервер упал", sequence_number=1)
    await insert_message(
        db_session, conv.id, text="смотрю логи", sequence_number=2, direction="outgoing"
    )
    for seq, text in enumerate(["later a", "later b", "later c"], start=10):
        await insert_message(db_session, conv.id, text=text, sequence_number=seq)
    await SummaryStateRepository().create(
        db_session,
        {"conversation_id": conv.id, "current_summary": "past", "checkpoint": 0},
    )
    await VectorRecordRepository().create(
        db_session,
        {
            "conversation_id": conv.id,
            "text": "Проблема с сервером",
            "kind": "topic",
            "embedding": _vec(0.9),
            "seq_from": 1,
            "seq_to": 2,
        },
    )
    llm = RecordingLLM()
    svc = _service(llm)
    event = await svc.build_context(
        db_session,
        BuildContextCommand(
            conversation_id=conv.id,
            channel="telegram",
            chat_id=50,
            batch_messages=[{"text": "что там с продом"}],
            last_n_messages=3,
        ),
    )
    assert event.retrieved[0].title == "Проблема с сервером"
    texts = [m.text for b in event.retrieved[0].batches for m in b.messages]
    assert "сервер упал" in texts
    assert "смотрю логи" in texts
    assert llm.embed_calls[-1][1] == "query"


@pytest.mark.asyncio
async def test_update_memory_skips_when_not_delivered(db_session):
    conv = await ConversationRepository().create(
        db_session,
        {"channel": "telegram", "chat_id": 31, "user_id": uuid.uuid4()},
    )
    llm = RecordingLLM()
    svc = _service(llm)
    event = await svc.update_memory(
        db_session,
        UpdateMemoryCommand(
            conversation_id=conv.id,
            channel="telegram",
            chat_id=31,
            outgoing_messages=["reply"],
            delivery_status="failed",
        ),
    )
    count = (await db_session.execute(select(func.count()).select_from(VectorRecord))).scalar()
    assert count == 0
    assert event.messages_count == 0
    assert event.summary_updated is False
    assert llm.embed_calls == []


@pytest.mark.asyncio
async def test_build_context_skips_topic_fully_in_recent(db_session):
    conv = await ConversationRepository().create(
        db_session,
        {"channel": "telegram", "chat_id": 51, "user_id": uuid.uuid4()},
    )
    await insert_message(db_session, conv.id, text="сервер упал", sequence_number=1)
    await VectorRecordRepository().create(
        db_session,
        {
            "conversation_id": conv.id,
            "text": "Проблема с сервером",
            "kind": "topic",
            "embedding": _vec(0.9),
            "seq_from": 1,
            "seq_to": 1,
        },
    )
    event = await _service(RecordingLLM()).build_context(
        db_session,
        BuildContextCommand(
            conversation_id=conv.id,
            channel="telegram",
            chat_id=51,
            last_n_messages=50,
        ),
    )
    assert event.retrieved == []


@pytest.mark.asyncio
async def test_build_context_dedups_same_title_by_id(db_session):
    conv = await ConversationRepository().create(
        db_session,
        {"channel": "telegram", "chat_id": 52, "user_id": uuid.uuid4()},
    )
    await insert_message(db_session, conv.id, text="now", sequence_number=20)
    for seq_from, seq_to, body in ((1, 2, "first"), (3, 4, "second")):
        await insert_message(db_session, conv.id, text=body, sequence_number=seq_from)
        await VectorRecordRepository().create(
            db_session,
            {
                "conversation_id": conv.id,
                "text": "Один заголовок",
                "kind": "topic",
                "embedding": _vec(0.9),
                "seq_from": seq_from,
                "seq_to": seq_to,
            },
        )
    event = await _service(RecordingLLM()).build_context(
        db_session,
        BuildContextCommand(
            conversation_id=conv.id,
            channel="telegram",
            chat_id=52,
            last_n_messages=1,
        ),
    )
    texts = [m.text for t in event.retrieved for b in t.batches for m in b.messages]
    assert "first" in texts
    assert "second" in texts


@pytest.mark.asyncio
async def test_cluster_retries_then_indexes(db_session):
    class Flaky(RecordingLLM):
        async def cluster_topics(self, numbered: str) -> str:
            self.cluster_calls.append(numbered)
            if len(self.cluster_calls) < 3:
                return "not-json"
            seqs = [int(line.split("|", 1)[0]) for line in numbered.splitlines() if line]
            return json.dumps(
                [
                    {"topic": "Приветствие", "ids": seqs[:5], "kind": "topic"},
                    {"topic": "хвост", "ids": seqs[5:], "kind": "topic"},
                ]
            )

    llm = Flaky()
    svc = _service(llm)
    event = await svc.process_batch(
        db_session,
        _cmd(
            chat_id=41,
            messages=[{"text": f"m{i}"} for i in range(20)],
        ),
    )
    await svc.maintain_memory(
        db_session,
        MaintainMemoryCommand(
            conversation_id=event.conversation_id,
            channel="telegram",
            chat_id=41,
            current_sequence=event.sequence_numbers[-1],
        ),
    )
    assert len(llm.cluster_calls) == 3
    rows = (await db_session.execute(select(VectorRecord))).scalars().all()
    assert len(rows) == 1
