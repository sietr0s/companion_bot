"""Общий транспорт in-memory producer и consumer."""

import asyncio
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class InMemoryMessage:
    topic: str
    payload: dict[str, Any]


class InMemoryTransport:
    """Очередь сообщений, общая для одной пары producer/consumer."""

    def __init__(self) -> None:
        self.queue: asyncio.Queue[InMemoryMessage] = asyncio.Queue()
