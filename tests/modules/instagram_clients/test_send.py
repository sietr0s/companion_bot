from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.bus.in_memory.consumer import InMemoryConsumer
from src.bus.in_memory.producer import InMemoryProducer
from src.bus.in_memory.transport import InMemoryTransport
from src.core.bus_topics import BusTopics
from src.modules.instagram_clients.handlers import register_handlers


@pytest.mark.asyncio
async def test_send_handler_calls_manager_and_publishes_sent():
    transport = InMemoryTransport()
    producer = InMemoryProducer(transport)
    consumer = InMemoryConsumer(transport)
    recorded: list[tuple[str, dict]] = []
    orig = producer.publish

    async def spy(topic: str, message: dict) -> None:
        recorded.append((topic, message))
        await orig(topic, message)

    producer.publish = spy  # type: ignore[method-assign]
    manager = AsyncMock()
    manager.send_text = AsyncMock(return_value="item-9")
    register_handlers(consumer, manager, producer)
    await consumer.start()
    account_id = uuid4()
    await producer.publish(
        BusTopics.IG_MESSAGE_SEND,
        {"account_id": str(account_id), "chat_id": 11, "text": "hi"},
    )
    await transport.queue.join()
    await consumer.stop()
    manager.send_text.assert_awaited_with(account_id, 11, "hi")
    sent = [m for t, m in recorded if t == BusTopics.IG_MESSAGE_SENT]
    assert sent and sent[0]["success"] is True
    assert sent[0]["message_id"] == "item-9"
