import uuid

import pytest

from src.modules.memory.constants import EMBEDDING_DIM
from src.modules.memory.models import Conversation, VectorRecord, Message
from src.modules.memory.repository import VectorRecordRepository, MessageRepository, ConversationRepository


def _vec(seed: float) -> list[float]:
    return [seed] * EMBEDDING_DIM


@pytest.mark.asyncio
async def test_search_similar_orders_by_cosine(db_session):
    conv_repo = ConversationRepository()
    conv = await conv_repo.create(db_session, {"telegram_chat_id": 1, "user_id": uuid.uuid4()})
    vec_repo = VectorRecordRepository()
    near = await vec_repo.create(db_session, {"conversation_id": conv.id, "text": "near", "embedding": _vec(1.0)})
    await vec_repo.create(db_session, {"conversation_id": conv.id, "text": "far", "embedding": _vec(-1.0)})
    other = await conv_repo.create(db_session, {"telegram_chat_id": 2, "user_id": uuid.uuid4()})
    await vec_repo.create(db_session, {"conversation_id": other.id, "text": "other", "embedding": _vec(1.0)})
    hits = await vec_repo.search_similar(db_session, conv.id, _vec(1.0), top_k=10)
    assert [h.text for h in hits] == ["near", "far"]
    assert hits[0].id == near.id


@pytest.mark.asyncio
async def test_get_after_checkpoint(db_session):
    conv_repo = ConversationRepository()
    conv = await conv_repo.create(db_session, {"telegram_chat_id": 3, "user_id": uuid.uuid4()})
    msg_repo = MessageRepository()
    for i, text in enumerate(["a", "b", "c"], start=1):
        await msg_repo.create(db_session, {
            "conversation_id": conv.id, "text": text, "direction": "incoming",
            "message_type": "text", "sequence_number": i,
        })
    got = await msg_repo.get_after_checkpoint(db_session, conv.id, checkpoint=1)
    assert [m.text for m in got] == ["b", "c"]
