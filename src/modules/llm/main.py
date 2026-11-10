"""llm composition and standalone application factory."""

from typing import Any

from fastapi import FastAPI

from src.core.application.module import ModuleContext, ModuleDefinition
from src.modules.llm.config import binding
from src.modules.llm.config.model import LlmConfigModel
from src.modules.llm.config.service import LlmConfigService
from src.modules.llm.dependencies import warmup_heavy_models
from src.modules.llm.handlers import register_handlers
from src.modules.llm.routers import router


async def prepare(context: ModuleContext) -> None:
    if not context.safe_mode:
        register_handlers(context.consumer, context.producer)


async def start(context: ModuleContext) -> None:
    if not context.safe_mode:
        await warmup_heavy_models()


def get_module() -> ModuleDefinition:
    return ModuleDefinition(
        name="llm",
        router=router,
        models=(LlmConfigModel,),
        configuration=LlmConfigService(),
        install_config=binding.install,
        clear_config=binding.clear,
        prepare=prepare,
        start=start,
    )


def create_app(*, ports: dict[str, Any] | None = None) -> FastAPI:
    """Run this module only; shared infrastructure is owned by the host."""
    from src.composition.application import create_service_app

    return create_service_app("llm", ports=ports)
