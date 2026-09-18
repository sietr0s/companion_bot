"""Registry of instagrapi clients. Sync Client calls run in a thread; one lock per account."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable
from typing import Any

from src.core.exceptions import NotFoundError

logger = logging.getLogger(__name__)


def _default_client_factory() -> Any:
    from instagrapi import Client

    return Client()


class InstagramClientManager:
    def __init__(self, client_factory: Callable[[], Any] | None = None) -> None:
        self._client_factory = client_factory or _default_client_factory
        self._clients: dict[uuid.UUID, Any] = {}
        self._locks: dict[uuid.UUID, asyncio.Lock] = {}

    def attach(self, account_id: uuid.UUID, client: Any) -> None:
        self._clients[account_id] = client
        self._locks.setdefault(account_id, asyncio.Lock())

    def get_client(self, account_id: uuid.UUID) -> Any:
        client = self._clients.get(account_id)
        if client is None:
            raise NotFoundError(detail=f"Instagram client {account_id} is not attached")
        return client

    def _lock(self, account_id: uuid.UUID) -> asyncio.Lock:
        lock = self._locks.get(account_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[account_id] = lock
        return lock

    async def send_text(self, account_id: uuid.UUID, thread_id: int, text: str) -> str:
        client = self.get_client(account_id)

        def _send() -> str:
            result = client.direct_send(text, thread_ids=[thread_id])
            if isinstance(result, dict):
                return str(result.get("id") or result.get("item_id") or "")
            item_id = getattr(result, "id", None)
            return str(item_id) if item_id is not None else ""

        async with self._lock(account_id):
            return await asyncio.to_thread(_send)

    async def stop_all(self) -> None:
        self._clients.clear()
        self._locks.clear()
