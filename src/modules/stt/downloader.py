"""Audio download port — implemented by TelegramClientManager."""

from pathlib import Path
from typing import Protocol
from uuid import UUID


class MediaDownloader(Protocol):
    async def download_voice(
        self, account_id: UUID, chat_id: int, message_id: int
    ) -> Path: ...
