"""tts composition and standalone application factory."""

from typing import Any

from fastapi import FastAPI

from src.core.application.module import ModuleContext, ModuleDefinition
from src.modules.tts.config import binding
from src.modules.tts.config.model import TtsConfigModel
from src.modules.tts.config.service import TtsConfigService
from src.modules.tts.handlers import register_handlers
from src.modules.tts.routers import router


async def prepare(context: ModuleContext) -> None:
    if not context.safe_mode:
        register_handlers(context.consumer, context.producer)


def get_module() -> ModuleDefinition:
    return ModuleDefinition(
        name="tts",
        router=router,
        models=(TtsConfigModel,),
        configuration=TtsConfigService(),
        install_config=binding.install,
        clear_config=binding.clear,
        prepare=prepare,
    )


def create_app(*, ports: dict[str, Any] | None = None) -> FastAPI:
    """Run this module only; shared infrastructure is owned by the host."""
    from src.composition.application import create_service_app

    return create_service_app("tts", ports=ports)
