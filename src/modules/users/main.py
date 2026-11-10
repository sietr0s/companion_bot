"""users composition and standalone application factory."""

from typing import Any

from fastapi import FastAPI

from src.core.application.module import ModuleContext, ModuleDefinition
from src.modules.users.config import binding
from src.modules.users.config.model import UsersConfigModel
from src.modules.users.config.service import UsersConfigService
from src.modules.users.handlers import register_handlers
from src.modules.users.models import User
from src.modules.users.routers import router


async def prepare(context: ModuleContext) -> None:
    register_handlers(context.consumer, context.producer)


def get_module() -> ModuleDefinition:
    return ModuleDefinition(
        name="users",
        router=router,
        models=(
            User,
            UsersConfigModel,
        ),
        configuration=UsersConfigService(),
        install_config=binding.install,
        clear_config=binding.clear,
        prepare=prepare,
    )


def create_app(*, ports: dict[str, Any] | None = None) -> FastAPI:
    """Run this module only; shared infrastructure is owned by the host."""
    from src.composition.application import create_service_app

    return create_service_app("users", ports=ports)
