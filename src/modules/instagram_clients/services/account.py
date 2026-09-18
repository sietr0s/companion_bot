"""DB-only Instagram account service. Login/poll live in later tasks."""

from typing import Any

from pydantic import BaseModel as PydanticModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.service import BaseService
from src.modules.instagram_clients.config import instagram_clients_settings
from src.modules.instagram_clients.models import InstagramAccount
from src.modules.instagram_clients.repository import InstagramAccountRepository
from src.modules.instagram_clients.services.settings import InstagramSettingsService


class InstagramAccountService(BaseService[InstagramAccountRepository, InstagramAccount]):
    def __init__(
        self,
        repository: InstagramAccountRepository,
        settings_service: InstagramSettingsService,
    ) -> None:
        super().__init__(repository)
        self.settings_service = settings_service

    async def create(
        self,
        session: AsyncSession,
        data: dict[str, Any] | PydanticModel,
    ) -> InstagramAccount:
        payload = data.model_dump(exclude_unset=True) if isinstance(data, PydanticModel) else dict(data)
        payload.setdefault("is_connected", False)
        payload.setdefault("session_file", "pending")
        account = await self.repository.create(session, payload)
        session_dir = instagram_clients_settings.INSTAGRAM_SESSION_DIR.rstrip("/\\")
        account = await self.repository.update(
            session,
            account,
            {"session_file": f"{session_dir}/{account.id}.json"},
        )
        await self.settings_service.create_default_settings(session, account.id)
        return account
