from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.core.bus_topics import BusTopics
from src.modules.telegram_clients.handlers import register_handlers
from src.bus.in_memory.consumer import InMemoryConsumer
from src.bus.in_memory.producer import InMemoryProducer
from src.bus.in_memory.transport import InMemoryTransport


@pytest.mark.asyncio
async def test_send_voice_handler_publishes_sent(tmp_path):
    transport = InMemoryTransport()
    producer = InMemoryProducer(transport)
    consumer = InMemoryConsumer(transport)
    path = tmp_path / "v.ogg"
    path.write_bytes(b"x")
    manager = AsyncMock()
    register_handlers(consumer, manager, producer)
    await consumer.start()
    account_id = uuid4()
    await producer.publish(
        BusTopics.TG_MESSAGE_SEND_VOICE,
        {
            "account_id": str(account_id),
            "chat_id": 1,
            "path": str(path),
            "text": "hi",
        },
    )
    await transport.queue.join()
    await consumer.stop()
    manager.send_voice.assert_awaited()
    assert not path.exists()
