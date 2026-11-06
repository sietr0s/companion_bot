"""Business reads remain usable after the SQLAlchemy session is detached."""

import pytest

from src.domain.chat import ChatRef
from src.modules.memory.domain import (
    ConversationState,
    HistoryMessage,
    HistoryWindow,
    IndexedTopic,
    NewMessage,
)
from src.modules.memory.repository import (
    ConversationRepository,
    MessageBatchRepository,
    MessageRepository,
    VectorRecordRepository,
)


@pytest.mark.asyncio
async def test_history_is_detached_domain_data(db_session):
    conversation = await ConversationRepository().get_or_create(
        db_session, channel="telegram", chat_id=4000
    )
    assert isinstance(conversation, ConversationState)
    await MessageBatchRepository().append_messages(
        db_session, conversation.id, "incoming", [NewMessage("hello"), NewMessage("world")]
    )
    history = await MessageRepository().get_last_messages(db_session, conversation.id)
    assert all(isinstance(message, HistoryMessage) for message in history)
    db_session.expunge_all()
    await db_session.close()
    batches = HistoryWindow(history).to_batches(
        ChatRef(channel="telegram", chat_id=4000, conversation_id=conversation.id)
    )
    assert len(batches) == 1
    assert [message.text for message in batches[0].messages] == ["hello", "world"]
    assert batches[0].conversation_id == conversation.id


@pytest.mark.asyncio
async def test_topic_repository_returns_domain_entities(db_session):
    conversation = await ConversationRepository().get_or_create(
        db_session, channel="telegram", chat_id=4001
    )
    topic = IndexedTopic(conversation_id=conversation.id, text="topic", seq_from=1, seq_to=3)
    repository = VectorRecordRepository()
    await repository.store_indexed_window(db_session, conversation.id, [topic], 3)
    saved = await repository.get_topic(db_session, topic.id)
    db_session.expunge_all()
    assert isinstance(saved, IndexedTopic)
    assert saved.title == "topic"
    assert saved.message_count == 3
