"""Conversation sequence numbers stay unique across batches."""

import uuid

import pytest
from sqlalchemy import select

from src.domain.chat import Batch
from src.modules.memory.models import Message
from src.modules.memory.repository import ConversationRepository
from src.modules.memory.schemas.events import ProcessBatchCommand
from tests.modules.memory.test_memory_retrieve import RecordingLLM, _service


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


@pytest.mark.asyncio
async def test_two_batches_get_distinct_sequence_numbers(db_session) -> None:
    svc = _service(RecordingLLM())
    chat_id = 99
    await svc.process_batch(
        db_session,
        _cmd(
            chat_id=chat_id,
            messages=[{"text": "a"}, {"text": "b"}],
        ),
    )
    await svc.process_batch(
        db_session,
        _cmd(
            chat_id=chat_id,
            messages=[{"text": "c"}],
        ),
    )
    conv = await ConversationRepository().get_by_chat_id(db_session, chat_id)
    assert conv is not None
    assert conv.last_sequence_number == 3
    result = await db_session.execute(select(Message).where(Message.conversation_id == conv.id))
    seqs = sorted(row.sequence_number for row in result.scalars().all())
    assert seqs == [1, 2, 3]


@pytest.mark.asyncio
async def test_two_accounts_same_chat_get_separate_conversations(db_session) -> None:
    svc = _service(RecordingLLM())
    chat_id = 4242
    acc_a = uuid.uuid4()
    acc_b = uuid.uuid4()
    first = await svc.process_batch(
        db_session,
        _cmd(
            chat_id=chat_id,
            account_id=acc_a,
            messages=[{"text": "from-a"}],
        ),
    )
    second = await svc.process_batch(
        db_session,
        _cmd(
            chat_id=chat_id,
            account_id=acc_b,
            messages=[{"text": "from-b"}],
        ),
    )
    assert first.conversation_id != second.conversation_id
    conv_a = await ConversationRepository().get_by_channel_chat_account(
        db_session, channel="telegram", chat_id=chat_id, account_id=acc_a
    )
    conv_b = await ConversationRepository().get_by_channel_chat_account(
        db_session, channel="telegram", chat_id=chat_id, account_id=acc_b
    )
    assert conv_a is not None and conv_b is not None
    assert conv_a.id != conv_b.id
    assert conv_a.last_sequence_number == 1
    assert conv_b.last_sequence_number == 1
