"""instagram_clients composition and standalone application factory."""

from typing import Any

from fastapi import FastAPI

from src.core.application.module import ModuleContext, ModuleDefinition
from src.core.database import create_async_session
from src.modules.instagram_clients.adapters.client_manager import InstagramClientManager
from src.modules.instagram_clients.config import binding
from src.modules.instagram_clients.config.model import InstagramClientsConfigModel
from src.modules.instagram_clients.config.service import InstagramClientsConfigService
from src.modules.instagram_clients.dependencies import (
    build_instagram_account_service,
    configure_instagram_client_manager,
)
from src.modules.instagram_clients.handlers import register_handlers
from src.modules.instagram_clients.models import (
    InstagramAccount,
    InstagramChatState,
    InstagramSettings,
)
from src.modules.instagram_clients.routers import router


def get_module() -> ModuleDefinition:
    manager = InstagramClientManager()
    configure_instagram_client_manager(manager)

    async def prepare(context: ModuleContext) -> None:
        if not context.safe_mode:
            register_handlers(context.consumer, manager, context.producer)

    async def start(context: ModuleContext) -> None:
        if not context.safe_mode:
            service = build_instagram_account_service(client_manager=manager)
            async with create_async_session() as session:
                await service.restore_sessions(session)

    async def quiesce(context: ModuleContext) -> None:
        await manager.stop_all()

    return ModuleDefinition(
        name="instagram_clients",
        router=router,
        models=(
            InstagramAccount,
            InstagramSettings,
            InstagramChatState,
            InstagramClientsConfigModel,
        ),
        configuration=InstagramClientsConfigService(),
        install_config=binding.install,
        clear_config=binding.clear,
        prepare=prepare,
        start=start,
        quiesce=quiesce,
    )


def create_app(*, ports: dict[str, Any] | None = None) -> FastAPI:
    """Run this module only; shared infrastructure is owned by the host."""
    from src.composition.application import create_service_app

    return create_service_app("instagram_clients", ports=ports)
