"""auth composition and standalone application factory."""

from typing import Any

from fastapi import FastAPI

from src.core.application.module import ModuleContext, ModuleDefinition
from src.core.database import create_async_session
from src.modules.auth.config import AuthBootstrapSettings, binding
from src.modules.auth.config.model import AuthConfigModel
from src.modules.auth.config.service import AuthConfigService
from src.modules.auth.models import Auth
from src.modules.auth.routers import router
from src.modules.auth.seed import seed_admin


async def prepare(context: ModuleContext) -> None:
    context.services["auth_bootstrap"] = AuthBootstrapSettings.model_validate({})


async def start(context: ModuleContext) -> None:
    async with create_async_session() as session:
        await seed_admin(session, context.producer, bootstrap=context.services["auth_bootstrap"])


def get_module() -> ModuleDefinition:
    return ModuleDefinition(
        name="auth",
        router=router,
        models=(
            Auth,
            AuthConfigModel,
        ),
        configuration=AuthConfigService(),
        install_config=binding.install,
        clear_config=binding.clear,
        prepare=prepare,
        start=start,
    )


def create_app(*, ports: dict[str, Any] | None = None) -> FastAPI:
    """Run this module only; shared infrastructure is owned by the host."""
    from src.composition.application import create_service_app

    return create_service_app("auth", ports=ports)
