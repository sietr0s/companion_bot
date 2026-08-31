"""In-process companion pipeline: telegram message -> reply command."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from src.bus.in_memory.consumer import InMemoryConsumer
from src.bus.in_memory.producer import InMemoryProducer
from src.bus.in_memory.transport import InMemoryTransport
from src.core.bus_topics import BusTopics
from src.modules.batching.handlers import register_handlers as register_batching
from src.modules.llm.handlers import register_handlers as register_llm
from src.modules.llm.service import LLMService
from src.modules.memory.handlers import register_handlers as register_memory
from src.modules.memory.models import VectorRecord
from src.modules.orchestrator.handlers import register_handlers as register_orchestrator
from src.modules.telegram_clients.handlers import register_handlers as register_tg
from tests.fakes.embedder import FakeEmbedder


class _SessionCM:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type is None:
            await self._session.commit()
        return False


async def _drain(transport: InMemoryTransport, timeout: float = 3.0) -> None:
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        remaining = max(0.01, deadline - asyncio.get_event_loop().time())
        try:
            await asyncio.wait_for(transport.queue.join(), timeout=remaining)
        except TimeoutError:
            return
        await asyncio.sleep(0.05)
        if transport.queue.empty():
            return


@pytest.mark.asyncio
async def test_incoming_message_reaches_telegram_send(db_session, monkeypatch):
    transport = InMemoryTransport()
    producer = InMemoryProducer(transport)
    consumer = InMemoryConsumer(transport, producer)

    monkeypatch.setattr(
        "src.modules.batching.handlers.create_async_session",
        lambda: _SessionCM(db_session),
    )
    monkeypatch.setattr(
        "src.modules.memory.handlers.create_async_session",
        lambda: _SessionCM(db_session),
    )

    fake = FakeEmbedder()
    monkeypatch.setattr("src.modules.llm.handlers.get_embedder", lambda: fake)
    monkeypatch.setattr("src.modules.memory.handlers.get_embedder", lambda: fake)

    pre_calls: list[list[str]] = []
    orig_pre = LLMService.retrieve_pre

    async def spy_pre(self, batch_messages):
        pre_calls.append(list(batch_messages))
        return await orig_pre(self, batch_messages)

    monkeypatch.setattr(LLMService, "retrieve_pre", spy_pre)

    manager = AsyncMock()
    manager.send_message = AsyncMock()

    register_batching(consumer, producer)
    register_memory(consumer, producer)
    register_llm(consumer, producer)
    register_orchestrator(consumer, producer)
    register_tg(consumer, manager, producer)

    account_id = uuid.uuid4()
    await consumer.start()
    await producer.publish(
        BusTopics.TG_MESSAGE_RECEIVED,
        {
            "account_id": str(account_id),
            "chat_id": 12345,
            "message_id": 1,
            "text": "hello companion",
            "sender": {"sender_id": 1},
        },
    )
    await _drain(transport)
    await consumer.stop()

    manager.send_message.assert_awaited()
    sent_args = manager.send_message.await_args
    assert sent_args.args[0] == account_id
    assert sent_args.args[1] == 12345
    assert "hello companion" in sent_args.args[2]

    assert pre_calls == [["hello companion"]]
    rows = (await db_session.execute(select(VectorRecord))).scalars().all()
    assert any("User: hello companion" in (r.text or "") for r in rows)
