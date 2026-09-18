import uuid

import pytest

from src.modules.memory.constants import EMBEDDING_DIM
from src.modules.memory.repository import (
    ConversationRepository,
    MessageRepository,
    VectorRecordRepository,
)
from tests.modules.memory.seed import insert_message


def _vec(seed: float) -> list[float]:
    return [seed] * EMBEDDING_DIM


@pytest.mark.asyncio
async def test_search_similar_orders_by_cosine(db_session):
    conv_repo = ConversationRepository()
    conv = await conv_repo.create(db_session, {"channel": "telegram", "chat_id": 1, "user_id": uuid.uuid4()})
    vec_repo = VectorRecordRepository()
    near = await vec_repo.create(
        db_session,
        {
            "conversation_id": conv.id,
            "text": "near",
            "embedding": _vec(1.0),
            "seq_from": 1,
            "seq_to": 1,
        },
    )
    await vec_repo.create(
        db_session,
        {
            "conversation_id": conv.id,
            "text": "far",
            "embedding": _vec(-1.0),
            "seq_from": 1,
            "seq_to": 1,
        },
    )
    other = await conv_repo.create(db_session, {"channel": "telegram", "chat_id": 2, "user_id": uuid.uuid4()})
    await vec_repo.create(
        db_session,
        {
            "conversation_id": other.id,
            "text": "other",
            "embedding": _vec(1.0),
            "seq_from": 1,
            "seq_to": 1,
        },
    )
    hits = await vec_repo.search_similar(db_session, conv.id, _vec(1.0), top_k=10)
    assert [h.text for h in hits] == ["near", "far"]
    assert hits[0].id == near.id


@pytest.mark.asyncio
async def test_search_similar_splits_topic_and_reference(db_session):
    conv_repo = ConversationRepository()
    conv = await conv_repo.create(db_session, {"channel": "telegram", "chat_id": 4, "user_id": uuid.uuid4()})
    other = await conv_repo.create(db_session, {"channel": "telegram", "chat_id": 5, "user_id": uuid.uuid4()})
    vec_repo = VectorRecordRepository()
    await vec_repo.create(
        db_session,
        {
            "conversation_id": conv.id,
            "text": "dialog topic",
            "embedding": _vec(1.0),
            "kind": "topic",
            "seq_from": 1,
            "seq_to": 1,
        },
    )
    await vec_repo.create(
        db_session,
        {
            "conversation_id": conv.id,
            "text": "local reference should not mix into topic",
            "kind": "reference",
            "embedding": _vec(1.0),
            "seq_from": 1,
            "seq_to": 1,
        },
    )
    await vec_repo.create(
        db_session,
        {
            "conversation_id": other.id,
            "text": "style example",
            "kind": "reference",
            "embedding": _vec(1.0),
            "seq_from": 1,
            "seq_to": 1,
        },
    )
    topics = await vec_repo.search_similar(db_session, conv.id, _vec(1.0), top_k=10, kind="topic")
    refs = await vec_repo.search_similar(db_session, None, _vec(1.0), top_k=10, kind="reference")
    assert [h.text for h in topics] == ["dialog topic"]
    assert {h.text for h in refs} == {
        "local reference should not mix into topic",
        "style example",
    }


@pytest.mark.asyncio
async def test_get_after_checkpoint(db_session):
    conv_repo = ConversationRepository()
    conv = await conv_repo.create(db_session, {"channel": "telegram", "chat_id": 3, "user_id": uuid.uuid4()})
    for i, text in enumerate(["a", "b", "c"], start=1):
        await insert_message(db_session, conv.id, text=text, sequence_number=i)
    got = await MessageRepository().get_after_checkpoint(db_session, conv.id, checkpoint=1)
    assert [m.text for m in got] == ["b", "c"]
