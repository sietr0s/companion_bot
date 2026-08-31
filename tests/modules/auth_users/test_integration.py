"""Auth больше не создаёт профиль users: это разные сущности."""

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
async def test_register_does_not_create_telegram_user(test_client_with_db: AsyncClient, admin_token: str):
    client = test_client_with_db
    register_resp = await client.post(
        "/api/v1/public/auth/register",
        json={
            "identifier": "cycle@test.com",
            "identifier_type": "email",
            "password": "testpassword123",
        },
    )
    assert register_resp.status_code in (200, 201), register_resp.text

    listed = await client.get(
        "/api/v1/public/users/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 0
