"""Lifecycle management for Telegram QR authentication sessions."""

import asyncio
import contextlib
import logging
import uuid
from collections.abc import Callable
from typing import Any

from telethon import TelegramClient

from src.core.exceptions import NotFoundError
from src.modules.telegram_clients.constants import QrAuthStatus

logger = logging.getLogger(__name__)


class QrAuthManager:
    """Own temporary QR state and background tasks independently of client I/O."""

    def __init__(
        self,
        create_client: Callable[[str], TelegramClient],
        get_session_path: Callable[[uuid.UUID], str],
        get_client: Callable[[uuid.UUID], TelegramClient | None],
        set_client: Callable[[uuid.UUID, TelegramClient], None],
        remove_client: Callable[[uuid.UUID], TelegramClient | None],
    ) -> None:
        self._create_client = create_client
        self._get_session_path = get_session_path
        self._get_client = get_client
        self._set_client = set_client
        self._remove_client = remove_client
        self._sessions: dict[uuid.UUID, dict[str, str]] = {}
        self._tasks: dict[uuid.UUID, asyncio.Task[None]] = {}

    async def _wait(self, account_id: uuid.UUID, qr: Any) -> None:
        try:
            await qr.wait()
            self._sessions[account_id] = {"status": QrAuthStatus.CONNECTED}
        except TimeoutError:
            self._sessions[account_id] = {
                "status": QrAuthStatus.EXPIRED,
                "message": "QR-код истёк",
            }
        except Exception as exc:
            self._sessions[account_id] = {
                "status": QrAuthStatus.ERROR,
                "message": str(exc),
            }
            logger.exception("QR login failed: account_id=%s", account_id)

    async def start(self, account_id: uuid.UUID) -> dict[str, Any]:
        if account_id in self._sessions:
            await self.cancel(account_id)
        client = self._create_client(self._get_session_path(account_id))
        try:
            await client.connect()
            qr = await client.qr_login()
        except Exception:
            await client.disconnect()
            raise
        self._set_client(account_id, client)
        self._sessions[account_id] = {"status": QrAuthStatus.PENDING}
        self._tasks[account_id] = asyncio.create_task(self._wait(account_id, qr))
        return {"qr_url": qr.url, "expires_at": getattr(qr, "timeout", None)}

    def status(self, account_id: uuid.UUID) -> dict[str, str]:
        session = self._sessions.get(account_id)
        if session is None:
            return {"status": QrAuthStatus.ERROR, "message": "QR-сессия не найдена"}
        return dict(session)

    async def cancel(self, account_id: uuid.UUID) -> None:
        task = self._tasks.pop(account_id, None)
        if task is not None and not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        client = self._remove_client(account_id)
        if client is not None:
            await client.disconnect()
        self._sessions.pop(account_id, None)

    async def complete(self, account_id: uuid.UUID) -> dict[str, Any]:
        client = self._get_client(account_id)
        if client is None:
            raise NotFoundError(detail=f"Клиент для account_id={account_id} не найден")
        me = await client.get_me()
        self._sessions.pop(account_id, None)
        self._tasks.pop(account_id, None)
        return {
            "first_name": me.first_name,
            "last_name": me.last_name,
            "username": me.username,
            "telegram_id": me.id,
        }

    async def stop(self) -> None:
        for account_id in list(self._tasks):
            await self.cancel(account_id)
