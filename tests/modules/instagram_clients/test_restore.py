"""Restore Instagram sessions from dumped settings JSON."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.instagram_clients.adapters.client_manager import InstagramClientManager
from src.modules.instagram_clients.config import instagram_clients_settings
from src.modules.instagram_clients.repository import (
    InstagramAccountRepository,
    InstagramChatStateRepository,
    InstagramSettingsRepository,
)
from src.modules.instagram_clients.services.account import InstagramAccountService
from src.modules.instagram_clients.services.settings import InstagramSettingsService


class DeadClient:
    def load_settings(self, path: str) -> None:
        raise RuntimeError("login_required")

    def account_info(self) -> dict:
        raise RuntimeError("login_required")


class LiveClient:
    def __init__(self) -> None:
        self.pk = 7
        self.username = "bot"
        self.full_name = "Bot"

    def load_settings(self, path: str) -> dict:
        return {}

    def account_info(self) -> dict:
        return {"pk": 7}

    def dump_settings(self, path: str) -> bool:
        Path(path).write_text("{}", encoding="utf-8")
        return True

    def direct_threads(self, amount: int = 20) -> list:
        return []


def _service(manager: InstagramClientManager) -> InstagramAccountService:
    return InstagramAccountService(
        repository=InstagramAccountRepository(),
        settings_service=InstagramSettingsService(InstagramSettingsRepository()),
        client_manager=manager,
        message_bus=AsyncMock(),
        chat_state_repository=InstagramChatStateRepository(),
    )


@pytest.mark.asyncio
async def test_restore_dead_session_marks_disconnected(
    db_session: AsyncSession, tmp_path: Path, monkeypatch
):
    monkeypatch.setattr(instagram_clients_settings, "INSTAGRAM_SESSION_DIR", str(tmp_path))
    manager = InstagramClientManager(client_factory=DeadClient)
    service = _service(manager)
    account = await service.create(db_session, {"username": "bot"})
    Path(account.session_file).write_text("{}", encoding="utf-8")
    await service.repository.update(db_session, account, {"is_connected": True, "instagram_pk": 7})
    await service.restore_sessions(db_session)
    fresh = await service.repository.get_by_id(db_session, account.id)
    assert fresh is not None
    assert fresh.is_connected is False


@pytest.mark.asyncio
async def test_restore_live_session_attaches(
    db_session: AsyncSession, tmp_path: Path, monkeypatch
):
    monkeypatch.setattr(instagram_clients_settings, "INSTAGRAM_SESSION_DIR", str(tmp_path))
    manager = InstagramClientManager(client_factory=LiveClient)
    service = _service(manager)
    account = await service.create(db_session, {"username": "bot"})
    Path(account.session_file).write_text("{}", encoding="utf-8")
    await service.restore_sessions(db_session)
    fresh = await service.repository.get_by_id(db_session, account.id)
    assert fresh is not None
    assert fresh.is_connected is True
    manager.get_client(account.id)
