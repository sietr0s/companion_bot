"""orchestrator composition and standalone application factory."""

from typing import Any

from fastapi import FastAPI

from src.core.application.module import ModuleContext, ModuleDefinition
from src.modules.orchestrator.config import binding
from src.modules.orchestrator.config.model import OrchestratorConfigModel
from src.modules.orchestrator.config.service import OrchestratorConfigService
from src.modules.orchestrator.handlers import register_handlers
from src.modules.orchestrator.routers import router


async def prepare(context: ModuleContext) -> None:
    if not context.safe_mode:
        context.services["orchestrator"] = register_handlers(context.consumer, context.producer)


async def stop(context: ModuleContext) -> None:
    service = context.services.get("orchestrator")
    if service is not None:
        await service.wait_background()


def get_module() -> ModuleDefinition:
    return ModuleDefinition(
        name="orchestrator",
        router=router,
        models=(OrchestratorConfigModel,),
        configuration=OrchestratorConfigService(),
        install_config=binding.install,
        clear_config=binding.clear,
        prepare=prepare,
        stop=stop,
    )


def create_app(*, ports: dict[str, Any] | None = None) -> FastAPI:
    """Run this module only; shared infrastructure is owned by the host."""
    from src.composition.application import create_service_app

    return create_service_app("orchestrator", ports=ports)
