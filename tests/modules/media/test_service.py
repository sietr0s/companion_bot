"""Тесты MediaService."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.bus.in_memory.producer import InMemoryProducer
from src.core.exceptions import NotFoundError
from src.modules.media.repository import StoredFileRepository
from src.modules.media.service import MediaService


class MockStorage:
    """Мок хранилища для тестов."""

    def __init__(self):
        self._files: dict[str, bytes] = {}

    async def put(self, key: str, data: bytes, content_type: str) -> str:
        self._files[key] = data
        return key

    async def get(self, key: str) -> bytes:
        return self._files[key]

    async def delete(self, key: str) -> None:
        self._files.pop(key, None)

    async def generate_url(self, key: str, expires: int = 3600) -> str:
        return f"/api/v1/public/media/download/{key}"


@pytest_asyncio.fixture
def service():
    return MediaService(
        repository=StoredFileRepository(),
        storage=MockStorage(),
        message_bus=InMemoryProducer(),
    )


class TestMediaServiceUpload:
    @pytest.mark.asyncio
    async def test_upload(self, db_session: AsyncSession, service):
        file = await service.upload(
            session=db_session,
            filename="photo.jpg",
            data=b"\xff\xd8\xff\xe0",
            content_type="image/jpeg",
            is_public=False,
        )
        assert file.filename == "photo.jpg"
        assert file.content_type == "image/jpeg"
        assert file.size_bytes == 4
        assert file.is_public is False
        assert file.storage_key

    @pytest.mark.asyncio
    async def test_upload_public(self, db_session: AsyncSession, service):
        file = await service.upload(
            session=db_session,
            filename="avatar.png",
            data=b"\x89PNG",
            content_type="image/png",
            is_public=True,
        )
        assert file.is_public is True


class TestMediaServiceGet:
    @pytest.mark.asyncio
    async def test_get_existing(self, db_session: AsyncSession, service):
        created = await service.upload(
            session=db_session,
            filename="doc.pdf",
            data=b"%PDF-1.4",
            content_type="application/pdf",
        )
        found = await service.get(db_session, created.id)
        assert found.id == created.id

    @pytest.mark.asyncio
    async def test_get_not_found(self, db_session: AsyncSession, service):
        with pytest.raises(NotFoundError):
            await service.get(db_session, uuid.uuid4())


class TestMediaServiceDownload:
    @pytest.mark.asyncio
    async def test_download(self, db_session: AsyncSession, service):
        data = b"file content here"
        created = await service.upload(
            session=db_session,
            filename="test.txt",
            data=data,
            content_type="text/plain",
        )
        stored_file, downloaded_data = await service.download(db_session, created.id)
        assert downloaded_data == data
        assert stored_file.filename == "test.txt"


class TestMediaServiceDelete:
    @pytest.mark.asyncio
    async def test_delete(self, db_session: AsyncSession, service):
        created = await service.upload(
            session=db_session,
            filename="del.txt",
            data=b"delete me",
            content_type="text/plain",
        )
        await service.delete(db_session, created.id)

        with pytest.raises(NotFoundError):
            await service.get(db_session, created.id)
