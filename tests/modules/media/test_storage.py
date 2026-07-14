"""Тесты файлового хранилища (LocalStorage)."""

import pytest

from src.modules.media.storage.local import LocalStorage, _generate_storage_key


class TestGenerateStorageKey:
    """Тесты генерации ключа хранилища."""

    def test_key_format(self):
        key = _generate_storage_key("photo.jpg")
        parts = key.split("/")
        assert len(parts) == 3
        assert len(parts[0]) == 2
        assert len(parts[1]) == 2
        assert parts[2].endswith(".jpg")

    def test_key_without_extension(self):
        key = _generate_storage_key("README")
        assert "/" in key
        assert not key.split("/")[-1].endswith(".")

    def test_key_uniqueness(self):
        key1 = _generate_storage_key("file.txt")
        key2 = _generate_storage_key("file.txt")
        assert key1 != key2


class TestLocalStorage:
    """Тесты LocalStorage с временной директорией."""

    @pytest.fixture
    def storage(self, tmp_path):
        return LocalStorage(base_path=str(tmp_path / "uploads"))

    @pytest.mark.asyncio
    async def test_put_and_get(self, storage):
        key = _generate_storage_key("test.txt")
        data = b"Hello, World!"
        result_key = await storage.put(key, data, "text/plain")
        assert result_key == key

        retrieved = await storage.get(key)
        assert retrieved == data

    @pytest.mark.asyncio
    async def test_delete(self, storage):
        key = _generate_storage_key("delete_me.txt")
        await storage.put(key, b"delete me", "text/plain")
        await storage.delete(key)

        file_path = storage._full_path(key)
        assert not file_path.exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, storage):
        await storage.delete("nonexistent/key.txt")

    @pytest.mark.asyncio
    async def test_generate_url(self, storage):
        url = await storage.generate_url("ab/cd/test.jpg")
        assert "/api/v1/public/media/" in url

    @pytest.mark.asyncio
    async def test_ensure_base_path(self, tmp_path):
        base = tmp_path / "new_uploads"
        storage = LocalStorage(base_path=str(base))
        assert not base.exists()
        storage.ensure_base_path()
        assert base.exists()

    @pytest.mark.asyncio
    async def test_put_creates_subdirs(self, storage):
        key = "ab/cd/deep_file.txt"
        await storage.put(key, b"deep", "text/plain")
        file_path = storage._full_path(key)
        assert file_path.exists()
        assert file_path.read_bytes() == b"deep"
