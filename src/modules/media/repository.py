"""
Репозиторий хранимых файлов.
"""

from src.base.repository import BaseRepository
from src.modules.media.models import StoredFile


class StoredFileRepository(BaseRepository[StoredFile]):
    """Репозиторий для CRUD-операций над StoredFile."""

    def __init__(self):
        super().__init__(StoredFile)
