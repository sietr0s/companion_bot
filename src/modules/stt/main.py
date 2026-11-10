"""stt composition and standalone application factory."""

from typing import Any

from fastapi import FastAPI

from src.core.application.module import ModuleContext, ModuleDefinition
from src.modules.stt.config import binding
from src.modules.stt.config.model import SttConfigModel
from src.modules.stt.config.service import SttConfigService
from src.modules.stt.dependencies import reset_provider, warmup_stt
from src.modules.stt.handlers import register_handlers
from src.modules.stt.routers import router


async def prepare(context: ModuleContext) -> None:
    if not context.safe_mode:
        downloader = context.services.get("media_downloader")
        if downloader is None:
            raise RuntimeError(
                "STT requires an injected MediaDownloader; standalone API is available in SAFE_MODE"
            )
        reset_provider()
        register_handlers(context.consumer, context.producer, downloader)


async def start(context: ModuleContext) -> None:
    if not context.safe_mode:
        await warmup_stt()


def get_module() -> ModuleDefinition:
    return ModuleDefinition(
        name="stt",
        router=router,
        models=(SttConfigModel,),
        configuration=SttConfigService(),
        install_config=binding.install,
        clear_config=binding.clear,
        prepare=prepare,
        start=start,
    )


def create_app(*, ports: dict[str, Any] | None = None) -> FastAPI:
    """Run this module only; shared infrastructure is owned by the host."""
    from src.composition.application import create_service_app

    return create_service_app("stt", ports=ports)
