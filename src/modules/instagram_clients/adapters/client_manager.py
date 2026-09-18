"""Registry of instagrapi clients. Sync Client calls run in a thread; one lock per account."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from src.core.exceptions import NotFoundError
from src.domain.chat import Person
from src.modules.instagram_clients.schemas.events import IgMessageReceived

logger = logging.getLogger(__name__)


def _default_client_factory() -> Any:
    from instagrapi import Client

    return Client()


class InstagramClientManager:
    def __init__(self, client_factory: Callable[[], Any] | None = None) -> None:
        self._client_factory = client_factory or _default_client_factory
        self._clients: dict[uuid.UUID, Any] = {}
        self._locks: dict[uuid.UUID, asyncio.Lock] = {}
        self._pending: dict[uuid.UUID, Any] = {}
        self._poll_tasks: dict[uuid.UUID, asyncio.Task] = {}

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

    def make_client(self) -> Any:
        return self._client_factory()

    async def login(self, account_id: uuid.UUID, username: str, password: str) -> Any:
        from src.modules.instagram_clients.adapters.login import raise_login_exception

        client = self._pending.get(account_id) or self.make_client()

        def _login() -> Any:
            try:
                client.login(username, password)
            except Exception as exc:
                raise_login_exception(exc)
            return client

        async with self._lock(account_id):
            try:
                logged = await asyncio.to_thread(_login)
            except Exception:
                self._pending[account_id] = client
                raise
            self.attach(account_id, logged)
            self._pending.pop(account_id, None)
            return logged

    async def complete_two_factor(self, account_id: uuid.UUID, code: str) -> Any:
        from src.modules.instagram_clients.adapters.login import raise_login_exception

        client = self._pending.get(account_id)
        if client is None:
            raise NotFoundError(detail="Нет незавершённого логина Instagram")

        def _finish() -> Any:
            try:
                client.two_factor_login(code)
            except Exception as exc:
                raise_login_exception(exc)
            return client

        async with self._lock(account_id):
            logged = await asyncio.to_thread(_finish)
            self.attach(account_id, logged)
            self._pending.pop(account_id, None)
            return logged

    async def complete_challenge(self, account_id: uuid.UUID, code: str) -> Any:
        from src.modules.instagram_clients.adapters.login import raise_login_exception

        client = self._pending.get(account_id)
        if client is None:
            raise NotFoundError(detail="Нет незавершённого логина Instagram")

        def _finish() -> Any:
            try:
                client.challenge_resolve(code)
            except Exception as exc:
                raise_login_exception(exc)
            return client

        async with self._lock(account_id):
            logged = await asyncio.to_thread(_finish)
            self.attach(account_id, logged)
            self._pending.pop(account_id, None)
            return logged

    async def dump_settings(self, account_id: uuid.UUID, path: str) -> None:
        client = self.get_client(account_id)

        def _dump() -> None:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            client.dump_settings(path)

        async with self._lock(account_id):
            await asyncio.to_thread(_dump)

    async def poll_once(
        self,
        account_id: uuid.UUID,
        *,
        own_pk: int,
        use_whitelist: bool,
        whitelist_user_pks: list[int],
        last_item_ids: dict[int, str],
    ) -> tuple[list[IgMessageReceived], dict[int, str]]:
        client = self.get_client(account_id)

        def _fetch() -> list[Any]:
            return list(client.direct_threads() or [])

        async with self._lock(account_id):
            threads = await asyncio.to_thread(_fetch)
        allowed = {int(pk) for pk in whitelist_user_pks}
        events: list[IgMessageReceived] = []
        cursors: dict[int, str] = {}
        for thread in threads:
            thread_id = int(getattr(thread, "id", 0) or 0)
            items = list(getattr(thread, "messages", None) or getattr(thread, "items", None) or [])
            items = sorted(items, key=_item_sort_key)
            last = last_item_ids.get(thread_id)
            if last is None and items:
                cursors[thread_id] = _item_id(items[-1])
                continue
            newest = last
            for item in items:
                iid = _item_id(item)
                if not _is_newer(iid, last):
                    continue
                newest = iid
                user_id = int(getattr(item, "user_id", 0) or 0)
                if user_id == int(own_pk):
                    continue
                if use_whitelist and user_id not in allowed:
                    continue
                text = getattr(item, "text", None)
                events.append(
                    IgMessageReceived(
                        account_id=account_id,
                        chat_id=thread_id,
                        message_id=iid,
                        sender=Person(sender_id=user_id),
                        text=text,
                    )
                )
            if newest is not None:
                cursors[thread_id] = newest
        return events, cursors

    async def start_poll(
        self,
        account_id: uuid.UUID,
        tick,
        *,
        interval_s: float | None = None,
    ) -> None:
        await self.stop_poll(account_id)
        delay = interval_s
        if delay is None:
            from src.modules.instagram_clients.config import instagram_clients_settings

            delay = instagram_clients_settings.INSTAGRAM_POLL_INTERVAL_S

        async def loop() -> None:
            while True:
                try:
                    await tick()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("instagram poll failed account=%s", account_id)
                await asyncio.sleep(delay)

        self._poll_tasks[account_id] = asyncio.create_task(loop())

    async def stop_poll(self, account_id: uuid.UUID) -> None:
        task = self._poll_tasks.pop(account_id, None)
        if task is not None and not task.done():
            task.cancel()

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
        for account_id in list(self._poll_tasks):
            await self.stop_poll(account_id)
        self._clients.clear()
        self._locks.clear()
        self._pending.clear()


def _item_id(item: Any) -> str:
    raw = getattr(item, "id", None)
    if raw is None and isinstance(item, dict):
        raw = item.get("id") or item.get("item_id")
    return str(raw or "")


def _item_sort_key(item: Any) -> tuple[int, str]:
    iid = _item_id(item)
    if iid.isdigit():
        return (0, str(int(iid)).zfill(20))
    return (1, iid)


def _is_newer(item_id: str, last: str | None) -> bool:
    if not item_id:
        return False
    if last is None:
        return True
    if item_id == last:
        return False
    if item_id.isdigit() and last.isdigit():
        return int(item_id) > int(last)
    return True
