"""Orchestrator pipeline state and outgoing memory writes."""

import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.bus.in_memory.consumer import InMemoryConsumer
from src.bus.in_memory.producer import InMemoryProducer
from src.bus.in_memory.transport import InMemoryTransport
from src.core.bus_topics import BusTopics
from src.modules.orchestrator.service import OrchestratorService


async def _drain(transport: InMemoryTransport, timeout: float = 2.0) -> None:
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        remaining = max(0.01, deadline - asyncio.get_event_loop().time())
        try:
            await asyncio.wait_for(transport.queue.join(), timeout=remaining)
        except TimeoutError:
            return
        await asyncio.sleep(0.02)
        if transport.queue.empty():
            return


@pytest.mark.asyncio
async def test_multi_bubble_send_persists_each_line_once() -> None:
    transport = InMemoryTransport()
    producer = InMemoryProducer(transport)
    consumer = InMemoryConsumer(transport)
    recorded: list[tuple[str, dict]] = []
    orig = producer.publish

    async def spy(topic: str, message: dict) -> None:
        recorded.append((topic, message))
        await orig(topic, message)

    producer.publish = spy  # type: ignore[method-assign]
    svc = OrchestratorService(consumer, producer)
    svc.register_all_handlers()
    await consumer.start()

    account_id = uuid4()
    chat_id = 42
    conversation_id = uuid4()

    await producer.publish(
        BusTopics.MEMORY_BATCH_PROCESSED,
        {
            "telegram_chat_id": chat_id,
            "telegram_account_id": str(account_id),
            "conversation_id": str(conversation_id),
            "messages": [{"text": "hi", "message_type": "text", "direction": "incoming"}],
        },
    )
    await _drain(transport)

    await producer.publish(
        BusTopics.MEMORY_CONTEXT_BUILT,
        {
            "telegram_chat_id": chat_id,
            "telegram_account_id": str(account_id),
            "conversation_id": str(conversation_id),
            "context": "hi",
        },
    )
    await _drain(transport)
    await producer.publish(
        BusTopics.BEHAVIOR_INTAKE_DECIDED,
        {
            "telegram_chat_id": chat_id,
            "telegram_account_id": str(account_id),
            "conversation_id": str(conversation_id),
            "action": "respond",
            "asked_voice": 0,
        },
    )
    await _drain(transport)
    await producer.publish(
        BusTopics.LLM_REPLY_GENERATED,
        {
            "telegram_chat_id": chat_id,
            "telegram_account_id": str(account_id),
            "messages": ["one", "two"],
        },
    )
    await _drain(transport)
    await producer.publish(
        BusTopics.BEHAVIOR_DELIVERY_DECIDED,
        {
            "telegram_chat_id": chat_id,
            "telegram_account_id": str(account_id),
            "action": "text",
            "text": "one. two",
        },
    )
    await _drain(transport)

    await producer.publish(
        BusTopics.TG_MESSAGE_SENT,
        {
            "telegram_account_id": str(account_id),
            "chat_id": chat_id,
            "text": "one",
            "success": True,
        },
    )
    await _drain(transport)
    await producer.publish(
        BusTopics.TG_MESSAGE_SENT,
        {
            "telegram_account_id": str(account_id),
            "chat_id": chat_id,
            "text": "two",
            "success": True,
        },
    )
    await _drain(transport)
    await consumer.stop()

    memory_updates = [payload for topic, payload in recorded if topic == BusTopics.MEMORY_UPDATE]
    outgoing = [msg for payload in memory_updates for msg in payload["outgoing_messages"]]
    assert outgoing == ["one", "two"]


@pytest.mark.asyncio
async def test_state_is_isolated_per_account_and_chat() -> None:
    transport = InMemoryTransport()
    producer = InMemoryProducer(transport)
    consumer = InMemoryConsumer(transport)
    svc = OrchestratorService(consumer, producer)
    svc.register_all_handlers()
    await consumer.start()

    acc_a = uuid4()
    acc_b = uuid4()
    chat_id = 7

    await producer.publish(
        BusTopics.MEMORY_BATCH_PROCESSED,
        {
            "telegram_chat_id": chat_id,
            "telegram_account_id": str(acc_a),
            "conversation_id": str(uuid4()),
            "messages": [],
        },
    )
    await _drain(transport)
    await producer.publish(
        BusTopics.MEMORY_BATCH_PROCESSED,
        {
            "telegram_chat_id": chat_id,
            "telegram_account_id": str(acc_b),
            "conversation_id": str(uuid4()),
            "messages": [],
        },
    )
    await _drain(transport)
    await consumer.stop()

    key_a = svc._state_key("telegram", acc_a, chat_id)
    key_b = svc._state_key("telegram", acc_b, chat_id)
    assert key_a != key_b
    assert svc._states[key_a].chat.conversation_id != svc._states[key_b].chat.conversation_id


@pytest.mark.asyncio
async def test_ignore_skips_llm(monkeypatch) -> None:
    monkeypatch.setattr("src.modules.orchestrator.service.asyncio.sleep", AsyncMock())

    transport = InMemoryTransport()
    producer = InMemoryProducer(transport)
    consumer = InMemoryConsumer(transport)
    recorded: list[tuple[str, dict]] = []
    orig = producer.publish

    async def spy(topic: str, message: dict) -> None:
        recorded.append((topic, message))
        await orig(topic, message)

    producer.publish = spy  # type: ignore[method-assign]
    svc = OrchestratorService(consumer, producer)
    svc.register_all_handlers()
    await consumer.start()
    account_id = uuid4()
    chat_id = 9
    cid = uuid4()
    await producer.publish(
        BusTopics.MEMORY_CONTEXT_BUILT,
        {
            "telegram_chat_id": chat_id,
            "telegram_account_id": str(account_id),
            "conversation_id": str(cid),
            "context": "x",
        },
    )
    await _drain(transport)
    await producer.publish(
        BusTopics.BEHAVIOR_INTAKE_DECIDED,
        {
            "telegram_chat_id": chat_id,
            "telegram_account_id": str(account_id),
            "conversation_id": str(cid),
            "action": "ignore",
        },
    )
    await _drain(transport)
    await consumer.stop()
    assert not any(t == BusTopics.LLM_GENERATE_REPLY for t, _ in recorded)


@pytest.mark.asyncio
async def test_voice_delivery_publishes_tts(monkeypatch) -> None:
    monkeypatch.setattr("src.modules.orchestrator.service.asyncio.sleep", AsyncMock())
    transport = InMemoryTransport()
    producer = InMemoryProducer(transport)
    consumer = InMemoryConsumer(transport)
    recorded: list[tuple[str, dict]] = []
    orig = producer.publish

    async def spy(topic: str, message: dict) -> None:
        recorded.append((topic, message))
        await orig(topic, message)

    producer.publish = spy  # type: ignore[method-assign]
    svc = OrchestratorService(consumer, producer)
    svc.register_all_handlers()
    await consumer.start()
    account_id = uuid4()
    chat_id = 3
    cid = uuid4()
    await producer.publish(
        BusTopics.MEMORY_CONTEXT_BUILT,
        {
            "telegram_chat_id": chat_id,
            "telegram_account_id": str(account_id),
            "conversation_id": str(cid),
            "context": "x",
        },
    )
    await _drain(transport)
    await producer.publish(
        BusTopics.LLM_REPLY_GENERATED,
        {
            "telegram_chat_id": chat_id,
            "telegram_account_id": str(account_id),
            "messages": ["hello there friend"],
        },
    )
    await _drain(transport)
    await producer.publish(
        BusTopics.BEHAVIOR_DELIVERY_DECIDED,
        {
            "telegram_chat_id": chat_id,
            "telegram_account_id": str(account_id),
            "action": "voice",
            "text": "hello there friend",
        },
    )
    await _drain(transport)
    await svc.wait_background()
    await _drain(transport)
    await consumer.stop()
    assert any(t == BusTopics.TTS_SYNTHESIZE for t, _ in recorded)
    assert not any(t == BusTopics.TG_MESSAGE_SEND for t, _ in recorded)


@pytest.mark.asyncio
async def test_tts_skip_sends_text_fallback(monkeypatch) -> None:
    monkeypatch.setattr("src.modules.orchestrator.service.asyncio.sleep", AsyncMock())
    transport = InMemoryTransport()
    producer = InMemoryProducer(transport)
    consumer = InMemoryConsumer(transport)
    recorded: list[tuple[str, dict]] = []
    orig = producer.publish

    async def spy(topic: str, message: dict) -> None:
        recorded.append((topic, message))
        await orig(topic, message)

    producer.publish = spy  # type: ignore[method-assign]
    svc = OrchestratorService(consumer, producer)
    svc.register_all_handlers()
    await consumer.start()
    account_id = uuid4()
    chat_id = 4
    await producer.publish(
        BusTopics.LLM_REPLY_GENERATED,
        {
            "telegram_chat_id": chat_id,
            "telegram_account_id": str(account_id),
            "messages": ["fallback"],
        },
    )
    await _drain(transport)
    await producer.publish(
        BusTopics.BEHAVIOR_DELIVERY_DECIDED,
        {
            "telegram_chat_id": chat_id,
            "telegram_account_id": str(account_id),
            "action": "voice",
            "text": "fallback",
        },
    )
    await _drain(transport)
    await svc.wait_background()
    await _drain(transport)
    await producer.publish(
        BusTopics.TTS_SYNTHESIZE_SKIPPED,
        {"account_id": str(account_id), "chat_id": chat_id, "reason": "stub"},
    )
    await _drain(transport)
    await consumer.stop()
    sent = [m for t, m in recorded if t == BusTopics.TG_MESSAGE_SEND]
    assert len(sent) == 1
    assert sent[0]["text"] == "fallback"
    assert not any(t == BusTopics.TG_MESSAGE_SEND_VOICE for t, _ in recorded)
