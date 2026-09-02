"""Тесты переподключения Kafka consumer без реального брокера."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from src.bus.kafka.consumer import KafkaConsumerRouter


class BrokenConsumer:
    def __init__(self) -> None:
        self.stop = AsyncMock()

    def __aiter__(self):
        return self

    async def __anext__(self):
        raise ConnectionError("connection lost")


class WaitingConsumer:
    def __init__(self) -> None:
        self.start = AsyncMock()
        self.stop = AsyncMock()
        self.waiting = asyncio.Event()

    def __aiter__(self):
        return self

    async def __anext__(self):
        await self.waiting.wait()
        raise StopAsyncIteration


@pytest.mark.asyncio
async def test_runtime_failure_recreates_consumer(monkeypatch) -> None:
    broken = BrokenConsumer()
    replacement = WaitingConsumer()
    real_sleep = asyncio.sleep

    def factory(*args, **kwargs):
        return replacement

    monkeypatch.setattr("src.bus.kafka.consumer.AIOKafkaConsumer", factory)
    monkeypatch.setattr("src.bus.kafka.consumer.asyncio.sleep", AsyncMock())

    router = KafkaConsumerRouter()
    router._topics = ("events",)
    router._consumer = broken

    task = asyncio.create_task(router._run_with_retry())
    for _ in range(20):
        if replacement.start.await_count:
            break
        await real_sleep(0)

    assert broken.stop.await_count == 1
    assert replacement.start.await_count == 1
    assert router._consumer is replacement

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await router._close_consumer()
