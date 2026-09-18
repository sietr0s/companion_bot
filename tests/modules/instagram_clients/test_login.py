"""Login / 2FA / session dump with an injected client (no live Instagram)."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.bus_topics import BusTopics
from src.modules.instagram_clients.adapters.client_manager import InstagramClientManager
from src.modules.instagram_clients.config import instagram_clients_settings
from src.modules.instagram_clients.exceptions import InstagramTwoFactorRequired
from src.modules.instagram_clients.repository import (
    InstagramAccountRepository,
    InstagramSettingsRepository,
)
from src.modules.instagram_clients.services.account import InstagramAccountService
from src.modules.instagram_clients.services.settings import InstagramSettingsService


class TwoFactorRequired(Exception):
    pass


class ScriptedClient:
    def __init__(self, *, require_2fa: bool = False) -> None:
        self.require_2fa = require_2fa
        self.dumped: str | None = None
        self.pk = 99
        self.username = "bot"
        self.full_name = "Bot Name"

    def login(self, username: str, password: str) -> bool:
        if self.require_2fa:
            raise TwoFactorRequired("two factor")
        return True

    def two_factor_login(self, verification_code: str) -> bool:
        return True

    def dump_settings(self, path: str) -> bool:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("{}", encoding="utf-8")
        self.dumped = path
        return True


def _service(manager: InstagramClientManager, producer) -> InstagramAccountService:
    return InstagramAccountService(
        repository=InstagramAccountRepository(),
        settings_service=InstagramSettingsService(InstagramSettingsRepository()),
        client_manager=manager,
        message_bus=producer,
    )


@pytest.mark.asyncio
async def test_login_success_dumps_settings(
    db_session: AsyncSession, tmp_path: Path, monkeypatch
):
    monkeypatch.setattr(instagram_clients_settings, "INSTAGRAM_SESSION_DIR", str(tmp_path))
    client = ScriptedClient()
    manager = InstagramClientManager(client_factory=lambda: client)
    producer = AsyncMock()
    service = _service(manager, producer)
    account = await service.create(db_session, {"username": "bot"})
    result = await service.login(db_session, account.id, username="bot", password="secret")
    assert result.is_connected is True
    assert result.instagram_pk == 99
    assert Path(result.session_file).is_file()
    assert client.dumped == result.session_file
    topics = [call.args[0] for call in producer.publish.await_args_list]
    assert BusTopics.IG_ACCOUNT_CONNECTED in topics


@pytest.mark.asyncio
async def test_login_two_factor_then_code(
    db_session: AsyncSession, tmp_path: Path, monkeypatch
):
    monkeypatch.setattr(instagram_clients_settings, "INSTAGRAM_SESSION_DIR", str(tmp_path))
    client = ScriptedClient(require_2fa=True)
    manager = InstagramClientManager(client_factory=lambda: client)
    producer = AsyncMock()
    service = _service(manager, producer)
    account = await service.create(db_session, {"username": "bot"})
    with pytest.raises(InstagramTwoFactorRequired):
        await service.login(db_session, account.id, username="bot", password="secret")
    result = await service.complete_two_factor(db_session, account.id, code="123456")
    assert result.is_connected is True
    assert Path(result.session_file).is_file()
