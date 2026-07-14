"""Интеграционные тесты публичных роутов /media/."""

import io
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db_session
from src.main import app


@pytest_asyncio.fixture
async def test_client_with_db() -> AsyncGenerator[AsyncClient, None]:
    """
    HTTP клиент с тестовой БД.
    Переопределяет get_db_session для использования test.db.
    """
    from tests.conftest import TestSessionLocal, test_engine

    # Создаём таблицы
    async with test_engine.begin() as conn:
        from src.base.model import Base

        await conn.run_sync(Base.metadata.create_all)

    # Генератор сессий
    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with TestSessionLocal() as session:
            yield session

    # Переопределяем зависимость get_db_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    # Создаём клиент
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Очищаем
    app.dependency_overrides.clear()

    # Удаляем таблицы
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def auth_headers(test_client_with_db: AsyncClient):
    """Создаёт Auth аккаунт и возвращает JWT токен."""
    from src.core.security import create_access_token
    from src.modules.auth.models import Auth
    from tests.conftest import TestSessionLocal

    account_id = uuid.uuid4()
    async with TestSessionLocal() as session:
        account = Auth(
            id=account_id,
            identifier="test@example.com",
            identifier_type="email",
            hashed_password="hashed",
            role="user",
        )
        session.add(account)
        await session.commit()

    token = create_access_token(str(account_id), "user")
    return {"Authorization": f"Bearer {token}"}


class TestPublicUpload:
    @pytest.mark.asyncio
    async def test_upload_requires_auth(self, test_client_with_db: AsyncClient):
        file_data = io.BytesIO(b"test content")
        resp = await test_client_with_db.post(
            "/api/v1/public/media/upload",
            files={"file": ("test.txt", file_data, "text/plain")},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_upload_success(self, test_client_with_db: AsyncClient, auth_headers: dict):
        file_data = io.BytesIO(b"hello world")
        resp = await test_client_with_db.post(
            "/api/v1/public/media/upload",
            files={"file": ("test.txt", file_data, "text/plain")},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["filename"] == "test.txt"
        assert body["content_type"] == "text/plain"
        assert body["is_public"] is False

    @pytest.mark.asyncio
    async def test_upload_public_file(self, test_client_with_db: AsyncClient, auth_headers: dict):
        file_data = io.BytesIO(b"public content")
        resp = await test_client_with_db.post(
            "/api/v1/public/media/upload",
            files={"file": ("pub.txt", file_data, "text/plain")},
            data={"is_public": "true"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["is_public"] is True


class TestPublicGet:
    @pytest.mark.asyncio
    async def test_get_public_file(self, test_client_with_db: AsyncClient, auth_headers: dict):
        file_data = io.BytesIO(b"public data")
        upload_resp = await test_client_with_db.post(
            "/api/v1/public/media/upload",
            files={"file": ("pub.txt", file_data, "text/plain")},
            data={"is_public": "true"},
            headers=auth_headers,
        )
        file_id = upload_resp.json()["id"]

        resp = await test_client_with_db.get(f"/api/v1/public/media/{file_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == file_id

    @pytest.mark.asyncio
    async def test_get_private_file_returns_404(
        self, test_client_with_db: AsyncClient, auth_headers: dict
    ):
        file_data = io.BytesIO(b"private data")
        upload_resp = await test_client_with_db.post(
            "/api/v1/public/media/upload",
            files={"file": ("priv.txt", file_data, "text/plain")},
            headers=auth_headers,
        )
        file_id = upload_resp.json()["id"]

        resp = await test_client_with_db.get(f"/api/v1/public/media/{file_id}")
        assert resp.status_code == 404


class TestPublicDownload:
    @pytest.mark.asyncio
    async def test_download_public_file(self, test_client_with_db: AsyncClient, auth_headers: dict):
        file_data = io.BytesIO(b"download me")
        upload_resp = await test_client_with_db.post(
            "/api/v1/public/media/upload",
            files={"file": ("dl.txt", file_data, "text/plain")},
            data={"is_public": "true"},
            headers=auth_headers,
        )
        file_id = upload_resp.json()["id"]

        resp = await test_client_with_db.get(f"/api/v1/public/media/{file_id}/download")
        assert resp.status_code == 200
        assert resp.content == b"download me"

    @pytest.mark.asyncio
    async def test_download_private_file_returns_404(
        self, test_client_with_db: AsyncClient, auth_headers: dict
    ):
        file_data = io.BytesIO(b"private")
        upload_resp = await test_client_with_db.post(
            "/api/v1/public/media/upload",
            files={"file": ("priv.txt", file_data, "text/plain")},
            headers=auth_headers,
        )
        file_id = upload_resp.json()["id"]

        resp = await test_client_with_db.get(f"/api/v1/public/media/{file_id}/download")
        assert resp.status_code == 404


class TestPublicDelete:
    @pytest.mark.asyncio
    async def test_delete_requires_auth(self, test_client_with_db: AsyncClient):
        resp = await test_client_with_db.delete(
            "/api/v1/public/media/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_success(self, test_client_with_db: AsyncClient, auth_headers: dict):
        file_data = io.BytesIO(b"to delete")
        upload_resp = await test_client_with_db.post(
            "/api/v1/public/media/upload",
            files={"file": ("del.txt", file_data, "text/plain")},
            headers=auth_headers,
        )
        file_id = upload_resp.json()["id"]

        url = f"/api/v1/public/media/{file_id}"
        resp = await test_client_with_db.delete(url, headers=auth_headers)
        assert resp.status_code == 204
