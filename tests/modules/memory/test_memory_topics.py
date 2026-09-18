import uuid

import pytest

from src.core.exceptions import NotFoundError
from src.modules.memory.constants import EMBEDDING_DIM
from src.modules.memory.repository import (
    ConversationRepository,
    VectorRecordRepository,
)
from tests.modules.memory.seed import insert_message
from tests.modules.memory.test_memory_retrieve import RecordingLLM, _service


def _vec(seed: float) -> list[float]:
    return [seed] * EMBEDDING_DIM


async def _seed_topic(db_session, chat_id: int = 77):
    conv = await ConversationRepository().create(
        db_session,
        {"channel": "telegram", "chat_id": chat_id, "user_id": uuid.uuid4()},
    )
    await insert_message(db_session, conv.id, text="сервер упал", sequence_number=1)
    await insert_message(
        db_session, conv.id, text="смотрю логи", sequence_number=2, direction="outgoing"
    )
    record = await VectorRecordRepository().create(
        db_session,
        {
            "conversation_id": conv.id,
            "text": "Проблема с сервером",
            "embedding": _vec(0.9),
            "seq_from": 1,
            "seq_to": 2,
            "partial": False,
        },
    )
    return conv, record


@pytest.mark.asyncio
async def test_list_topics_for_conversation(db_session):
    conv, record = await _seed_topic(db_session)
    other = await ConversationRepository().create(
        db_session,
        {"channel": "telegram", "chat_id": 78, "user_id": uuid.uuid4()},
    )
    await VectorRecordRepository().create(
        db_session,
        {
            "conversation_id": other.id,
            "text": "чужой диалог",
            "embedding": _vec(0.1),
            "seq_from": 1,
            "seq_to": 1,
        },
    )
    svc = _service(RecordingLLM())
    topics = await svc.list_topics(db_session, conv.id)
    assert len(topics) == 1
    topic = topics[0]
    assert topic.id == record.id
    assert topic.title == "Проблема с сервером"
    assert topic.seq_from == 1
    assert topic.seq_to == 2
    assert topic.message_count == 2
    assert topic.partial is False


@pytest.mark.asyncio
async def test_get_topic_includes_messages(db_session):
    conv, record = await _seed_topic(db_session)
    svc = _service(RecordingLLM())
    detail = await svc.get_topic(db_session, conv.id, record.id)
    assert [m.text for m in detail.messages] == ["сервер упал", "смотрю логи"]
    assert detail.title == "Проблема с сервером"


@pytest.mark.asyncio
async def test_get_topic_wrong_conversation(db_session):
    conv, record = await _seed_topic(db_session)
    other = await ConversationRepository().create(
        db_session,
        {"channel": "telegram", "chat_id": 79, "user_id": uuid.uuid4()},
    )
    svc = _service(RecordingLLM())
    with pytest.raises(NotFoundError):
        await svc.get_topic(db_session, other.id, record.id)
