"""Failure paths must not leave partial history or partial vector indexes."""

from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from src.modules.memory.domain import IndexedTopic, NewMessage
from src.modules.memory.models import (
    Conversation,
    Message,
    MessageBatch,
    SummaryState,
    VectorRecord,
)
from src.modules.memory.repository import (
    ConversationRepository,
    MessageBatchRepository,
    VectorRecordRepository,
)
from src.modules.memory.services.maintenance import MemoryMaintenance
from tests.modules.memory.seed import insert_message
from tests.modules.memory.test_memory_retrieve import RecordingLLM


@pytest.mark.asyncio
async def test_failed_batch_rolls_back_sequences_and_all_messages(db_session):
    conversation = await ConversationRepository().create(
        db_session, {"channel": "telegram", "chat_id": 700}
    )
    conversation_id = conversation.id
    with pytest.raises(IntegrityError):
        await MessageBatchRepository().append_messages(
            db_session,
            conversation_id,
            "incoming",
            [
                NewMessage(text="valid", message_type="text"),
                NewMessage(text=None, message_type="text"),
            ],
        )
    last = await db_session.scalar(
        select(Conversation.last_sequence_number).where(Conversation.id == conversation_id)
    )
    assert last == 0
    assert await db_session.scalar(select(func.count()).select_from(Message)) == 0
    assert await db_session.scalar(select(func.count()).select_from(MessageBatch)) == 0
    assert (
        await MessageBatchRepository().append_messages(
            db_session, conversation_id, "incoming", [NewMessage(text="retry", message_type="text")]
        )
        == 1
    )


@pytest.mark.asyncio
async def test_failed_index_does_not_save_a_topic_or_advance_checkpoint(db_session):
    conversation = await ConversationRepository().create(
        db_session, {"channel": "telegram", "chat_id": 701}
    )
    conversation_id = conversation.id
    await VectorRecordRepository().store_indexed_window(db_session, conversation_id, [], 5)
    with pytest.raises(IntegrityError):
        await VectorRecordRepository().store_indexed_window(
            db_session,
            conversation_id,
            [
                IndexedTopic(conversation_id=conversation_id, text="valid", seq_from=6, seq_to=7),
                IndexedTopic(conversation_id=conversation_id, text=None, seq_from=8, seq_to=9),
            ],
            9,
        )
    assert await db_session.scalar(select(func.count()).select_from(VectorRecord)) == 0
    assert await db_session.scalar(select(SummaryState.cluster_checkpoint)) == 5


@pytest.mark.asyncio
async def test_duplicate_batch_does_not_consume_sequence_numbers(db_session):
    conversation = await ConversationRepository().create(
        db_session, {"channel": "telegram", "chat_id": 702}
    )
    conversation_id = conversation.id
    batch_id = uuid4()
    batches = MessageBatchRepository()
    await batches.append_messages(
        db_session, conversation_id, "incoming", [NewMessage(text="one")], batch_id=batch_id
    )
    with pytest.raises(IntegrityError):
        await batches.append_messages(
            db_session,
            conversation_id,
            "incoming",
            [NewMessage(text="duplicate")],
            batch_id=batch_id,
        )
    assert (
        await db_session.scalar(
            select(Conversation.last_sequence_number).where(Conversation.id == conversation_id)
        )
        == 1
    )
    assert await db_session.scalar(select(func.count()).select_from(Message)) == 1


@pytest.mark.asyncio
async def test_summary_does_not_include_messages_beyond_its_checkpoint(db_session):
    from src.modules.memory.repository import MessageRepository, SummaryStateRepository

    conversation = await ConversationRepository().create(
        db_session, {"channel": "telegram", "chat_id": 703, "last_sequence_number": 55}
    )
    for number in range(1, 56):
        await insert_message(db_session, conversation.id, text=f"m{number}", sequence_number=number)
    llm = RecordingLLM()
    maintenance = MemoryMaintenance(
        MessageRepository(), SummaryStateRepository(), VectorRecordRepository(), llm
    )
    assert await maintenance._maybe_summarize(
        db_session, conversation_id=conversation.id, current_sequence=50
    )
    assert llm.summarize_calls == [[f"m{number}" for number in range(1, 51)]]
    assert await db_session.scalar(select(SummaryState.checkpoint)) == 50
