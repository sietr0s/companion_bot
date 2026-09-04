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
from src.modules.behavior.classifiers import FakeIntakeClassifier
from src.modules.behavior.engine import Decision
from src.modules.behavior.handlers import register_handlers as register_behavior
from src.modules.behavior.repository import BehaviorRepository
from src.modules.behavior.service import BehaviorService
from src.modules.llm.handlers import register_handlers as register_llm
from src.modules.llm.providers.stub import StubChat
from src.modules.llm.service import LLMService
from src.modules.memory.handlers import register_handlers as register_memory
from src.modules.memory.models import VectorRecord
from src.modules.orchestrator.handlers import register_handlers as register_orchestrator
from src.modules.stt.handlers import register_handlers as register_stt
from src.modules.stt.providers.stub import StubStt
from src.modules.telegram_clients.handlers import register_handlers as register_tg
from tests.fakes.embedder import FakeEmbedder


class _SessionCM:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type is None:
            try:
                await self._session.commit()
            except Exception:
                await self._session.rollback()
                raise
        else:
            await self._session.rollback()
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


def _patch_behavior(monkeypatch, db_session, *, needs_reply=1, action=None):
    def _decide(policy, ctx, rng, temperature=None):
        picked = action or policy.fallback
        return Decision(action=picked, scores={a: 1.0 for a in policy.legal_actions}, blocked={})

    monkeypatch.setattr("src.modules.behavior.service.decide", _decide)
    monkeypatch.setattr("src.modules.orchestrator.service.asyncio.sleep", AsyncMock())

    def build(producer):
        return BehaviorService(producer, BehaviorRepository(), FakeIntakeClassifier(needs_reply=needs_reply))

    monkeypatch.setattr("src.modules.behavior.handlers.build_behavior_service", build)
    monkeypatch.setattr(
        "src.modules.behavior.handlers.create_async_session",
        lambda: _SessionCM(db_session),
    )


@pytest.mark.asyncio
async def test_incoming_message_reaches_telegram_send(db_session, monkeypatch):
    transport = InMemoryTransport()
    producer = InMemoryProducer(transport)
    consumer = InMemoryConsumer(transport)

    monkeypatch.setattr(
        "src.modules.memory.handlers.create_async_session",
        lambda: _SessionCM(db_session),
    )

    fake = FakeEmbedder()
    stub = StubChat()
    monkeypatch.setattr("src.modules.llm.handlers.get_embedder", lambda: fake)
    monkeypatch.setattr("src.modules.llm.handlers.get_chat_provider", lambda: stub)
    monkeypatch.setattr("src.modules.llm.dependencies.get_embedder", lambda: fake)
    monkeypatch.setattr("src.modules.llm.dependencies.get_chat_provider", lambda: stub)
    monkeypatch.setattr("src.modules.llm.dependencies._chat", stub)
    monkeypatch.setattr("src.core.config.settings.BATCH_MAX_SIZE", 1)
    monkeypatch.setattr("src.core.config.settings.BATCH_IDLE_SECONDS", 0)
    _patch_behavior(monkeypatch, db_session)

    pre_calls: list[list[str]] = []
    orig_pre = LLMService.retrieve_pre

    async def spy_pre(self, batch_messages):
        texts = [
            getattr(item, "text", None) or item.get("text") if not isinstance(item, str) else item
            for item in batch_messages
        ]
        pre_calls.append(texts)
        return await orig_pre(self, batch_messages)

    monkeypatch.setattr(LLMService, "retrieve_pre", spy_pre)

    manager = AsyncMock()
    manager.send_message = AsyncMock()

    register_batching(consumer, producer)
    register_memory(consumer, producer)
    register_behavior(consumer, producer)
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
    assert rows == []


@pytest.mark.asyncio
async def test_voice_message_is_transcribed_then_replied(db_session, monkeypatch, tmp_path):
    transport = InMemoryTransport()
    producer = InMemoryProducer(transport)
    consumer = InMemoryConsumer(transport)

    monkeypatch.setattr(
        "src.modules.memory.handlers.create_async_session",
        lambda: _SessionCM(db_session),
    )

    fake = FakeEmbedder()
    stub = StubChat()
    monkeypatch.setattr("src.modules.llm.handlers.get_embedder", lambda: fake)
    monkeypatch.setattr("src.modules.llm.handlers.get_chat_provider", lambda: stub)
    monkeypatch.setattr("src.modules.llm.dependencies.get_embedder", lambda: fake)
    monkeypatch.setattr("src.modules.llm.dependencies.get_chat_provider", lambda: stub)
    monkeypatch.setattr("src.modules.llm.dependencies._chat", stub)
    monkeypatch.setattr("src.core.config.settings.BATCH_MAX_SIZE", 1)
    monkeypatch.setattr("src.core.config.settings.BATCH_IDLE_SECONDS", 0)
    _patch_behavior(monkeypatch, db_session)

    class FakeDl:
        async def download_voice(self, account_id, chat_id, message_id):
            path = tmp_path / f"{message_id}.ogg"
            path.write_bytes(b"ogg")
            return path

    manager = AsyncMock()
    manager.send_message = AsyncMock()

    register_batching(consumer, producer)
    register_memory(consumer, producer)
    register_behavior(consumer, producer)
    register_llm(consumer, producer)
    register_stt(consumer, producer, FakeDl(), StubStt())
    register_orchestrator(consumer, producer)
    register_tg(consumer, manager, producer)

    account_id = uuid.uuid4()
    await consumer.start()
    await producer.publish(
        BusTopics.TG_MESSAGE_RECEIVED,
        {
            "account_id": str(account_id),
            "chat_id": 12345,
            "message_id": 7,
            "text": "",
            "sender": {"sender_id": 1},
            "media": [{"telegram_id": 99, "type": "voice"}],
        },
    )
    await _drain(transport)
    await consumer.stop()

    manager.send_message.assert_awaited()
    assert "transcribed" in manager.send_message.await_args.args[2]


@pytest.mark.asyncio
async def test_ignore_does_not_send(db_session, monkeypatch):
    transport = InMemoryTransport()
    producer = InMemoryProducer(transport)
    consumer = InMemoryConsumer(transport)
    monkeypatch.setattr(
        "src.modules.memory.handlers.create_async_session",
        lambda: _SessionCM(db_session),
    )
    fake = FakeEmbedder()
    stub = StubChat()
    monkeypatch.setattr("src.modules.llm.handlers.get_embedder", lambda: fake)
    monkeypatch.setattr("src.modules.llm.handlers.get_chat_provider", lambda: stub)
    monkeypatch.setattr("src.modules.llm.dependencies.get_embedder", lambda: fake)
    monkeypatch.setattr("src.modules.llm.dependencies.get_chat_provider", lambda: stub)
    monkeypatch.setattr("src.modules.llm.dependencies._chat", stub)
    monkeypatch.setattr("src.core.config.settings.BATCH_MAX_SIZE", 1)
    monkeypatch.setattr("src.core.config.settings.BATCH_IDLE_SECONDS", 0)
    _patch_behavior(monkeypatch, db_session, action="ignore")
    manager = AsyncMock()
    manager.send_message = AsyncMock()
    register_batching(consumer, producer)
    register_memory(consumer, producer)
    register_behavior(consumer, producer)
    register_llm(consumer, producer)
    register_orchestrator(consumer, producer)
    register_tg(consumer, manager, producer)
    await consumer.start()
    await producer.publish(
        BusTopics.TG_MESSAGE_RECEIVED,
        {
            "account_id": str(uuid.uuid4()),
            "chat_id": 99,
            "message_id": 1,
            "text": "whatever",
            "sender": {"sender_id": 1},
        },
    )
    await _drain(transport)
    await consumer.stop()
    manager.send_message.assert_not_awaited()
