"""Instagram account service: persistence plus login via InstagramClientManager."""

from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel as PydanticModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.service import BaseService
from src.bus.interface import MessageProducer
from src.core.bus_topics import BusTopics
from src.core.exceptions import NotFoundError
from src.modules.instagram_clients.adapters.client_manager import InstagramClientManager
from src.modules.instagram_clients.config import instagram_clients_settings
from src.modules.instagram_clients.models import InstagramAccount
from src.modules.instagram_clients.repository import (
    InstagramAccountRepository,
    InstagramChatStateRepository,
)
from src.modules.instagram_clients.schemas.events import IgAccountConnected
from src.modules.instagram_clients.services.settings import InstagramSettingsService


class InstagramAccountService(BaseService[InstagramAccountRepository, InstagramAccount]):
    def __init__(
        self,
        repository: InstagramAccountRepository,
        settings_service: InstagramSettingsService,
        client_manager: InstagramClientManager | None = None,
        message_bus: MessageProducer | None = None,
        chat_state_repository: InstagramChatStateRepository | None = None,
    ) -> None:
        super().__init__(repository)
        self.settings_service = settings_service
        self.client_manager = client_manager
        self.message_bus = message_bus
        self.chat_state_repository = chat_state_repository

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

    async def login(
        self,
        session: AsyncSession,
        account_id: UUID,
        *,
        username: str,
        password: str,
    ) -> InstagramAccount:
        account = await self._require_account(session, account_id)
        manager = self._require_manager()
        client = await manager.login(account_id, username, password)
        return await self._mark_connected(session, account, client)

    async def complete_two_factor(
        self, session: AsyncSession, account_id: UUID, *, code: str
    ) -> InstagramAccount:
        account = await self._require_account(session, account_id)
        manager = self._require_manager()
        client = await manager.complete_two_factor(account_id, code)
        return await self._mark_connected(session, account, client)

    async def complete_challenge(
        self, session: AsyncSession, account_id: UUID, *, code: str
    ) -> InstagramAccount:
        account = await self._require_account(session, account_id)
        manager = self._require_manager()
        client = await manager.complete_challenge(account_id, code)
        return await self._mark_connected(session, account, client)

    def _require_manager(self) -> InstagramClientManager:
        if self.client_manager is None:
            raise RuntimeError("InstagramClientManager is required for login")
        return self.client_manager

    async def _require_account(
        self, session: AsyncSession, account_id: UUID
    ) -> InstagramAccount:
        account = await self.repository.get_by_id(session, account_id)
        if account is None:
            raise NotFoundError(detail="Instagram-аккаунт не найден")
        return account

    async def _mark_connected(
        self, session: AsyncSession, account: InstagramAccount, client: Any
    ) -> InstagramAccount:
        manager = self._require_manager()
        await manager.dump_settings(account.id, account.session_file)
        pk = getattr(client, "pk", None) or getattr(client, "user_id", None)
        full_name = getattr(client, "full_name", None)
        username = getattr(client, "username", None) or account.username
        account = await self.repository.update(
            session,
            account,
            {
                "is_connected": True,
                "instagram_pk": int(pk) if pk is not None else account.instagram_pk,
                "full_name": full_name or account.full_name,
                "username": username,
            },
        )
        if self.message_bus is not None:
            await self.message_bus.publish(
                BusTopics.IG_ACCOUNT_CONNECTED,
                IgAccountConnected(
                    account_id=account.id,
                    username=account.username,
                    instagram_pk=account.instagram_pk,
                ).model_dump(mode="json"),
            )
        await self._start_polling(account.id)
        return account

    async def poll_and_publish(self, session: AsyncSession, account_id: UUID) -> int:
        account = await self._require_account(session, account_id)
        if account.instagram_pk is None:
            return 0
        manager = self._require_manager()
        settings = await self.settings_service.create_default_settings(session, account_id)
        last_item_ids: dict[int, str] = {}
        if self.chat_state_repository is not None:
            states = await self.chat_state_repository.get_all_by_account(session, account_id)
            last_item_ids = {int(row.thread_id): row.last_item_id for row in states}
        events, cursors = await manager.poll_once(
            account_id,
            own_pk=int(account.instagram_pk),
            use_whitelist=bool(settings.use_whitelist),
            whitelist_user_pks=list(settings.whitelist_user_pks or []),
            last_item_ids=last_item_ids,
        )
        if self.chat_state_repository is not None:
            for thread_id, item_id in cursors.items():
                await self.chat_state_repository.upsert_last_item_id(
                    session, account_id, thread_id, item_id
                )
        if self.message_bus is not None:
            for event in events:
                await self.message_bus.publish(
                    BusTopics.IG_MESSAGE_RECEIVED, event.model_dump(mode="json")
                )
        return len(events)

    async def restore_sessions(self, session: AsyncSession) -> None:
        accounts = await self.repository.get_all(session, limit=1000)
        manager = self._require_manager()
        for account in accounts:
            path = Path(account.session_file) if account.session_file else None
            if path is None or not path.is_file():
                if account.is_connected:
                    await self.repository.update(session, account, {"is_connected": False})
                continue
            ok = await manager.restore_session(account.id, account.session_file)
            await self.repository.update(session, account, {"is_connected": ok})
            if ok:
                await self._start_polling(account.id)

    async def _start_polling(self, account_id: UUID) -> None:
        from src.core.database import create_async_session

        manager = self._require_manager()

        async def tick() -> None:
            async with create_async_session() as poll_session:
                await self.poll_and_publish(poll_session, account_id)

        await manager.start_poll(account_id, tick)
