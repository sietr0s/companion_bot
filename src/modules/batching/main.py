"""batching composition and standalone application factory."""

from typing import Any

from fastapi import FastAPI

from src.core.application.module import ModuleContext, ModuleDefinition
from src.modules.batching.config import binding, get_settings
from src.modules.batching.config.model import BatchingConfigModel
from src.modules.batching.config.service import BatchingConfigService
from src.modules.batching.handlers import register_handlers
from src.modules.batching.routers import router


async def prepare(context: ModuleContext) -> None:
    if not context.safe_mode:
        context.services["batching"] = register_handlers(
            context.consumer, context.producer, get_settings()
        )


async def stop(context: ModuleContext) -> None:
    service = context.services.get("batching")
    if service is not None:
        await service.stop()


def get_module() -> ModuleDefinition:
    return ModuleDefinition(
        name="batching",
        router=router,
        models=(BatchingConfigModel,),
        configuration=BatchingConfigService(),
        install_config=binding.install,
        clear_config=binding.clear,
        prepare=prepare,
        stop=stop,
    )


def create_app(*, ports: dict[str, Any] | None = None) -> FastAPI:
    """Run this module only; shared infrastructure is owned by the host."""
    from src.composition.application import create_service_app

    return create_service_app("batching", ports=ports)
