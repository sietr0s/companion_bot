"""
Интеграционные тесты модуля media.

Проверяют загрузку, скачивание и удаление файлов через реальное API.
"""

import io
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


class TestMediaInternalCRUD:
    """Интеграционные тесты internal API для медиа."""

    @pytest.mark.asyncio
    async def test_upload_file_internal(self, test_client_with_db: AsyncClient):
        """Загрузка файла через internal API."""
        client = test_client_with_db

        # Загружаем файл (internal API не требует owner_auth_id)
        file_content = b"Test file content for media integration test"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        data = {"is_public": "false"}

        upload_resp = await client.post("/internal/media/upload", data=data, files=files)
        assert upload_resp.status_code == 201
        uploaded = upload_resp.json()
        assert uploaded["filename"] == "test.txt"

        # Очистка
        await client.delete(f"/internal/media/{uploaded['id']}")

    @pytest.mark.asyncio
    async def test_get_file_info_internal(self, test_client_with_db: AsyncClient):
        """Получение информации о файле через internal API."""
        client = test_client_with_db

        # Загружаем файл
        file_content = b"Get file test content"
        files = {"file": ("get_test.txt", io.BytesIO(file_content), "text/plain")}
        data = {"is_public": "true"}

        upload_resp = await client.post("/internal/media/upload", data=data, files=files)
        file_id = upload_resp.json()["id"]

        # Получаем информацию о файле
        get_resp = await client.get(f"/internal/media/{file_id}")
        assert get_resp.status_code == 200
        file_info = get_resp.json()
        assert file_info["id"] == file_id
        assert file_info["filename"] == "get_test.txt"

        # Очистка
        await client.delete(f"/internal/media/{file_id}")

    @pytest.mark.asyncio
    async def test_download_file_internal(self, test_client_with_db: AsyncClient):
        """Скачивание файла через internal API."""
        client = test_client_with_db

        # Загружаем файл
        original_content = b"Download test content 12345"
        files = {
            "file": (
                "download_test.bin",
                io.BytesIO(original_content),
                "application/octet-stream",
            )
        }
        data = {"is_public": "false"}

        upload_resp = await client.post("/internal/media/upload", data=data, files=files)
        file_id = upload_resp.json()["id"]

        # Скачиваем файл
        download_resp = await client.get(f"/internal/media/{file_id}/download")
        assert download_resp.status_code == 200
        downloaded_content = download_resp.content
        assert downloaded_content == original_content

        # Очистка
        await client.delete(f"/internal/media/{file_id}")

    @pytest.mark.asyncio
    async def test_delete_file_internal(self, test_client_with_db: AsyncClient):
        """Удаление файла через internal API."""
        client = test_client_with_db

        # Загружаем файл
        file_content = b"Delete test content"
        files = {"file": ("delete_test.txt", io.BytesIO(file_content), "text/plain")}
        data = {"is_public": "false"}

        upload_resp = await client.post("/internal/media/upload", data=data, files=files)
        file_id = upload_resp.json()["id"]

        # Удаляем файл
        delete_resp = await client.delete(f"/internal/media/{file_id}")
        assert delete_resp.status_code == 204

        # Проверяем, что файл удалён
        get_resp = await client.get(f"/internal/media/{file_id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_files_by_owner(self, test_client_with_db: AsyncClient):
        """Получение списка файлов с фильтрацией."""
        client = test_client_with_db

        # Загружаем несколько файлов
        file_ids = []
        for i in range(3):
            file_content = f"File {i} content".encode()
            files = {"file": (f"file_{i}.txt", io.BytesIO(file_content), "text/plain")}
            data = {"is_public": "true"}

            upload_resp = await client.post("/internal/media/upload", data=data, files=files)
            file_ids.append(upload_resp.json()["id"])

        # Получаем список всех файлов
        list_resp = await client.get("/internal/media/")
        assert list_resp.status_code == 200
        files = list_resp.json()
        assert len(files) >= 3

        # Очистка
        for file_id in file_ids:
            await client.delete(f"/internal/media/{file_id}")


class TestMediaPublicAPI:
    """Интеграционные тесты public API для медиа."""

    @pytest.mark.asyncio
    async def test_upload_file_public(self, test_client_with_db: AsyncClient):
        """Загрузка файла через public API с JWT."""
        client = test_client_with_db

        # Создаём Auth аккаунт
        register_resp = await client.post(
            "/internal/auth/",
            json={
                "identifier": "public-upload@test.com",
                "identifier_type": "email",
                "hashed_password": "testpassword123",
            },
        )
        auth_id = register_resp.json()["id"]

        # Получаем JWT токен
        from src.core.security import create_access_token

        token = create_access_token(auth_id, "user")
        headers = {"Authorization": f"Bearer {token}"}

        # Загружаем файл
        file_content = b"Public upload test content"
        files = {"file": ("public_test.txt", io.BytesIO(file_content), "text/plain")}
        data = {"is_public": "true"}

        upload_resp = await client.post(
            "/public/media/upload", data=data, files=files, headers=headers
        )
        assert upload_resp.status_code == 201
        uploaded = upload_resp.json()
        assert uploaded["filename"] == "public_test.txt"

        # Очистка
        await client.delete(f"/internal/media/{uploaded['id']}")
        await client.delete(f"/internal/auth/{auth_id}")

    @pytest.mark.asyncio
    async def test_download_public_file(self, test_client_with_db: AsyncClient):
        """Скачивание публичного файла без аутентификации."""
        client = test_client_with_db

        # Создаём публичный файл (через internal API)
        original_content = b"Public download test content"
        files = {
            "file": (
                "public_file.bin",
                io.BytesIO(original_content),
                "application/octet-stream",
            )
        }
        data = {"is_public": "true"}

        upload_resp = await client.post("/internal/media/upload", data=data, files=files)
        file_id = upload_resp.json()["id"]

        # Скачиваем публичный файл без токена
        download_resp = await client.get(f"/public/media/{file_id}/download")
        assert download_resp.status_code == 200
        downloaded_content = download_resp.content
        assert downloaded_content == original_content

        # Очистка
        await client.delete(f"/internal/media/{file_id}")

    @pytest.mark.asyncio
    async def test_download_private_file_requires_auth(self, test_client_with_db: AsyncClient):
        """Скачивание приватного файла требует аутентификации."""
        client = test_client_with_db

        # Загружаем приватный файл через internal API
        file_content = b"Private download test"
        files = {"file": ("private_file.bin", io.BytesIO(file_content), "application/octet-stream")}
        data = {"is_public": "false"}

        upload_resp = await client.post("/internal/media/upload", data=data, files=files)
        file_id = upload_resp.json()["id"]

        # Попытка скачать без токена должна вернуть 401 или 404
        download_resp = await client.get(f"/public/media/{file_id}/download")
        assert download_resp.status_code in [401, 404]

        # Очистка
        await client.delete(f"/internal/media/{file_id}")
