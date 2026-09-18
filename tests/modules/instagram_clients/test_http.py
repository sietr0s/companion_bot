"""Public HTTP for Instagram accounts, settings, whitelist (admin JWT)."""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db_session
from src.main import app


@pytest_asyncio.fixture
async def test_client_with_db() -> AsyncGenerator[AsyncClient, None]:
    from tests.conftest import TestSessionLocal, test_engine

    async with test_engine.begin() as conn:
        from src.base.model import Base

        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_create_account(test_client_with_db: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = await test_client_with_db.post(
        "/api/v1/public/instagram/accounts/",
        json={"username": "x"},
        headers=headers,
    )
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert body["username"] == "x"
    assert "password" not in body
    assert body["is_connected"] is False
    assert body["session_file"]
    assert "instagram" in body["session_file"]


@pytest.mark.asyncio
async def test_whitelist_add_and_remove(test_client_with_db: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    created = await test_client_with_db.post(
        "/api/v1/public/instagram/accounts/",
        json={"username": "bot"},
        headers=headers,
    )
    assert created.status_code in (200, 201), created.text
    account_id = created.json()["id"]
    added = await test_client_with_db.post(
        f"/api/v1/public/instagram/{account_id}/whitelist",
        json={"user_pk": 101},
        headers=headers,
    )
    assert added.status_code == 200, added.text
    assert 101 in (added.json()["whitelist_user_pks"] or [])
    removed = await test_client_with_db.delete(
        f"/api/v1/public/instagram/{account_id}/whitelist/101",
        headers=headers,
    )
    assert removed.status_code == 200, removed.text
    assert 101 not in (removed.json()["whitelist_user_pks"] or [])
