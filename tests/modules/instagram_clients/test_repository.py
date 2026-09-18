"""Persistence for Instagram accounts, settings, and Direct read cursors."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.instagram_clients.repository import (
    InstagramAccountRepository,
    InstagramChatStateRepository,
    InstagramSettingsRepository,
)


@pytest.mark.asyncio
async def test_create_account(db_session: AsyncSession):
    repo = InstagramAccountRepository()
    acc = await repo.create(
        db_session,
        {
            "username": "bot",
            "session_file": "sessions/instagram/x.json",
            "is_connected": False,
        },
    )
    assert acc.id is not None
    assert acc.username == "bot"
    assert acc.instagram_pk is None
    assert acc.is_connected is False


@pytest.mark.asyncio
async def test_settings_by_account_id(db_session: AsyncSession):
    accounts = InstagramAccountRepository()
    settings_repo = InstagramSettingsRepository()
    acc = await accounts.create(
        db_session,
        {"username": "bot", "session_file": "sessions/instagram/x.json", "is_connected": False},
    )
    row = await settings_repo.create(
        db_session,
        {
            "account_id": acc.id,
            "use_whitelist": True,
            "whitelist_user_pks": [101],
        },
    )
    found = await settings_repo.get_by_account_id(db_session, acc.id)
    assert found is not None
    assert found.id == row.id
    assert found.whitelist_user_pks == [101]


@pytest.mark.asyncio
async def test_chat_state_upsert_last_item_id(db_session: AsyncSession):
    accounts = InstagramAccountRepository()
    states = InstagramChatStateRepository()
    acc = await accounts.create(
        db_session,
        {"username": "bot", "session_file": "sessions/instagram/x.json", "is_connected": False},
    )
    first = await states.upsert_last_item_id(db_session, acc.id, thread_id=11, item_id="100")
    second = await states.upsert_last_item_id(db_session, acc.id, thread_id=11, item_id="200")
    assert first.id == second.id
    assert second.last_item_id == "200"
    found = await states.get_by_account_and_thread(db_session, acc.id, 11)
    assert found is not None
    assert found.last_item_id == "200"
