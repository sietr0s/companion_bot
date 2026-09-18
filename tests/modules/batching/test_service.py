"""In-memory batching: idle wait then flush, or flush at max_size."""

import asyncio
import uuid

import pytest

from src.bus.in_memory.producer import InMemoryProducer
from src.bus.in_memory.transport import InMemoryTransport
from src.core.bus_topics import BusTopics
from src.domain.chat import Message
from src.modules.batching.schemas.events import AddMessageCommand
from src.modules.batching.service import BatchService


def _cmd(chat_id: int, content: str, account_id=None, channel="telegram") -> AddMessageCommand:
    return AddMessageCommand(
        channel=channel,
        chat_id=chat_id,
        account_id=account_id or uuid.uuid4(),
        message=Message(text=content),
    )


def _texts(messages) -> list[str]:
    return [m.text if hasattr(m, "text") else m["text"] for m in messages]


def _batch_texts(batch_payload) -> list[str]:
    if isinstance(batch_payload, dict):
        return _texts(batch_payload.get("messages") or [])
    return _texts(getattr(batch_payload, "messages", []))


@pytest.mark.asyncio
async def test_instagram_and_telegram_same_ids_do_not_share_batch():
    transport = InMemoryTransport()
    producer = InMemoryProducer(transport)
    service = BatchService(producer, max_size=2, idle_timeout=10.0)
    account_id = uuid.uuid4()
    tg = await service.add_incoming_message(_cmd(1, "tg", account_id, channel="telegram"))
    ig = await service.add_incoming_message(_cmd(1, "ig", account_id, channel="instagram"))
    assert tg is None and ig is None
    tg_ready = await service.add_incoming_message(_cmd(1, "tg2", account_id, channel="telegram"))
    assert _batch_texts(tg_ready.batch) == ["tg", "tg2"]
    assert tg_ready.channel == "telegram"


@pytest.mark.asyncio
async def test_add_message_publishes_ready_when_full():
    transport = InMemoryTransport()
    producer = InMemoryProducer(transport)
    service = BatchService(producer, max_size=1, idle_timeout=10.0)

    event = await service.add_incoming_message(_cmd(1, "hello"))

    assert event is not None
    assert _batch_texts(event.batch) == ["hello"]
    published = transport.queue.get_nowait()
    assert published.topic == BusTopics.BATCH_READY
    assert _batch_texts(published.payload["batch"]) == ["hello"]


@pytest.mark.asyncio
async def test_add_message_holds_until_max_size():
    transport = InMemoryTransport()
    producer = InMemoryProducer(transport)
    service = BatchService(producer, max_size=2, idle_timeout=10.0)
    account_id = uuid.uuid4()

    first = await service.add_incoming_message(_cmd(2, "one", account_id))
    assert first is None
    assert transport.queue.empty()

    second = await service.add_incoming_message(_cmd(2, "two", account_id))
    assert second is not None
    assert _batch_texts(second.batch) == ["one", "two"]


@pytest.mark.asyncio
async def test_idle_timeout_flushes_partial_batch():
    transport = InMemoryTransport()
    producer = InMemoryProducer(transport)
    service = BatchService(producer, max_size=10, idle_timeout=0.05)

    event = await service.add_incoming_message(_cmd(3, "alone"))
    assert event is None
    assert transport.queue.empty()

    await asyncio.sleep(0.12)

    published = transport.queue.get_nowait()
    assert published.topic == BusTopics.BATCH_READY
    assert _batch_texts(published.payload["batch"]) == ["alone"]


@pytest.mark.asyncio
async def test_new_message_resets_idle_timer():
    transport = InMemoryTransport()
    producer = InMemoryProducer(transport)
    service = BatchService(producer, max_size=10, idle_timeout=0.1)
    account_id = uuid.uuid4()

    await service.add_incoming_message(_cmd(4, "one", account_id))
    await asyncio.sleep(0.05)
    await service.add_incoming_message(_cmd(4, "two", account_id))
    await asyncio.sleep(0.05)
    assert transport.queue.empty()

    await asyncio.sleep(0.12)
    published = transport.queue.get_nowait()
    assert _batch_texts(published.payload["batch"]) == ["one", "two"]


@pytest.mark.asyncio
async def test_same_chat_different_accounts_keep_separate_batches():
    transport = InMemoryTransport()
    producer = InMemoryProducer(transport)
    service = BatchService(producer, max_size=2, idle_timeout=10.0)
    acc_a = uuid.uuid4()
    acc_b = uuid.uuid4()
    chat_id = 5

    first = await service.add_incoming_message(_cmd(chat_id, "a", acc_a))
    second = await service.add_incoming_message(_cmd(chat_id, "b", acc_b))
    assert first is None
    assert second is None
    assert transport.queue.empty()

    flushed = await service.add_incoming_message(_cmd(chat_id, "c", acc_a))
    assert flushed is not None
    account_from_batch = (
        flushed.batch["account_id"]
        if isinstance(flushed.batch, dict)
        else flushed.batch.account_id
    )
    assert account_from_batch == acc_a
    assert _batch_texts(flushed.batch) == ["a", "c"]
    assert transport.queue.qsize() == 1
