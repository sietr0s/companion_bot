"""telegram_clients composition and standalone application factory."""

from typing import Any

from fastapi import FastAPI

from src.core.application.module import ModuleContext, ModuleDefinition
from src.core.database import create_async_session
from src.modules.telegram_clients.adapters.client_manager import TelegramClientManager
from src.modules.telegram_clients.config import binding
from src.modules.telegram_clients.config.model import TelegramClientsConfigModel
from src.modules.telegram_clients.config.service import TelegramClientsConfigService
from src.modules.telegram_clients.dependencies import (
    configure_telegram_client_manager,
    get_telegram_client_service_factory,
)
from src.modules.telegram_clients.handlers import register_handlers
from src.modules.telegram_clients.models import TelegramAccount, TelegramChatState, TelegramSettings
from src.modules.telegram_clients.routers import router


def get_module() -> ModuleDefinition:
    manager = TelegramClientManager()
    configure_telegram_client_manager(manager)

    async def prepare(context: ModuleContext) -> None:
        if not context.safe_mode:
            context.services.setdefault("media_downloader", manager)
            register_handlers(context.consumer, manager, context.producer)

    async def start(context: ModuleContext) -> None:
        if not context.safe_mode:
            service = get_telegram_client_service_factory(client_manager=manager)
            async with create_async_session() as session:
                await service.restore_tg_sessions(session)
            async with create_async_session() as session:
                accounts = await service.get_active_accounts(session)
                for account in accounts:
                    await service.read_unread_messages(session, account.id)

    async def quiesce(context: ModuleContext) -> None:
        await manager.stop_all()

    return ModuleDefinition(
        name="telegram_clients",
        router=router,
        models=(
            TelegramAccount,
            TelegramSettings,
            TelegramChatState,
            TelegramClientsConfigModel,
        ),
        configuration=TelegramClientsConfigService(),
        install_config=binding.install,
        clear_config=binding.clear,
        prepare=prepare,
        start=start,
        quiesce=quiesce,
    )


def create_app(*, ports: dict[str, Any] | None = None) -> FastAPI:
    """Run this module only; shared infrastructure is owned by the host."""
    from src.composition.application import create_service_app

    return create_service_app("telegram_clients", ports=ports)
