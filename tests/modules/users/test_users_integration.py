"""Интеграция HTTP CRUD собеседников (только admin JWT)."""

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


class TestUsersCRUD:
    @pytest.mark.asyncio
    async def test_admin_crud(
        self,
        test_client_with_db: AsyncClient,
        admin_token: str,
        auth_token: str,
    ) -> None:
        admin = {"Authorization": f"Bearer {admin_token}"}
        user_headers = {"Authorization": f"Bearer {auth_token}"}

        forbidden = await test_client_with_db.get("/api/v1/public/users/", headers=user_headers)
        assert forbidden.status_code == 401

        created = await test_client_with_db.post(
            "/api/v1/public/users/",
            json={"telegram_id": 10001, "first_name": "Alice", "notes": "коротко"},
            headers=admin,
        )
        assert created.status_code == 201, created.text
        body = created.json()
        user_id = body["id"]
        assert body["telegram_id"] == 10001
        assert body["notes"] == "коротко"

        listed = await test_client_with_db.get("/api/v1/public/users/", headers=admin)
        assert listed.status_code == 200
        assert listed.json()["total"] >= 1

        updated = await test_client_with_db.put(
            f"/api/v1/public/users/{user_id}",
            json={"first_name": "Alicia", "notes": "любит мемы"},
            headers=admin,
        )
        assert updated.status_code == 200
        assert updated.json()["first_name"] == "Alicia"

        deleted = await test_client_with_db.delete(
            f"/api/v1/public/users/{user_id}",
            headers=admin,
        )
        assert deleted.status_code == 204
