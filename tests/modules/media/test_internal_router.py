"""Интеграционные тесты internal-роутов /internal/media/."""

import io
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db_session
from src.core.config import settings
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
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-Internal-Service-Key": settings.INTERNAL_SERVICE_KEY},
    ) as client:
        yield client

    # Очищаем
    app.dependency_overrides.clear()

    # Удаляем таблицы
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


class TestInternalUpload:
    @pytest.mark.asyncio
    async def test_upload_without_auth(self, test_client_with_db: AsyncClient):
        file_data = io.BytesIO(b"internal upload")
        resp = await test_client_with_db.post(
            "/internal/media/upload",
            files={"file": ("int.txt", file_data, "text/plain")},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["filename"] == "int.txt"
        assert body["is_public"] is False


class TestInternalGet:
    @pytest.mark.asyncio
    async def test_get_any_file(self, test_client_with_db: AsyncClient):
        file_data = io.BytesIO(b"internal get")
        upload_resp = await test_client_with_db.post(
            "/internal/media/upload",
            files={"file": ("get.txt", file_data, "text/plain")},
        )
        file_id = upload_resp.json()["id"]

        resp = await test_client_with_db.get(f"/internal/media/{file_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == file_id

    @pytest.mark.asyncio
    async def test_get_private_file(self, test_client_with_db: AsyncClient):
        file_data = io.BytesIO(b"private internal")
        upload_resp = await test_client_with_db.post(
            "/internal/media/upload",
            files={"file": ("priv.txt", file_data, "text/plain")},
        )
        file_id = upload_resp.json()["id"]

        # Internal-роут отдаёт приватные файлы
        resp = await test_client_with_db.get(f"/internal/media/{file_id}")
        assert resp.status_code == 200


class TestInternalDownload:
    @pytest.mark.asyncio
    async def test_download_any_file(self, test_client_with_db: AsyncClient):
        file_data = io.BytesIO(b"download internal")
        upload_resp = await test_client_with_db.post(
            "/internal/media/upload",
            files={"file": ("dl.txt", file_data, "text/plain")},
        )
        file_id = upload_resp.json()["id"]

        resp = await test_client_with_db.get(f"/internal/media/{file_id}/download")
        assert resp.status_code == 200
        assert resp.content == b"download internal"


class TestInternalDelete:
    @pytest.mark.asyncio
    async def test_delete_without_auth(self, test_client_with_db: AsyncClient):
        file_data = io.BytesIO(b"to delete internal")
        upload_resp = await test_client_with_db.post(
            "/internal/media/upload",
            files={"file": ("del.txt", file_data, "text/plain")},
        )
        file_id = upload_resp.json()["id"]

        resp = await test_client_with_db.delete(f"/internal/media/{file_id}")
        assert resp.status_code == 204

        # Файл удалён
        resp = await test_client_with_db.get(f"/internal/media/{file_id}")
        assert resp.status_code == 404
