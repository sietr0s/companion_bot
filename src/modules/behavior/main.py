"""behavior composition and standalone application factory."""

from typing import Any

from fastapi import FastAPI

from src.core.application.module import ModuleContext, ModuleDefinition
from src.modules.behavior.config import binding
from src.modules.behavior.config.model import BehaviorConfigModel
from src.modules.behavior.config.service import BehaviorConfigService
from src.modules.behavior.dependencies import build_behavior_service
from src.modules.behavior.handlers import register_handlers
from src.modules.behavior.models import BehaviorAccountState, BehaviorChatState
from src.modules.behavior.routers import router


async def prepare(context: ModuleContext) -> None:
    if not context.safe_mode:
        chat = context.services.get("chat_provider")
        if chat is None:
            raise RuntimeError("Behavior requires a ChatProvider port from composition")
        register_handlers(
            context.consumer,
            context.producer,
            service=build_behavior_service(context.producer, chat=chat),
        )


def get_module() -> ModuleDefinition:
    return ModuleDefinition(
        name="behavior",
        router=router,
        models=(
            BehaviorAccountState,
            BehaviorChatState,
            BehaviorConfigModel,
        ),
        configuration=BehaviorConfigService(),
        install_config=binding.install,
        clear_config=binding.clear,
        prepare=prepare,
    )


def create_app(*, ports: dict[str, Any] | None = None) -> FastAPI:
    """Run this module only; shared infrastructure is owned by the host."""
    from src.composition.application import create_service_app

    return create_service_app("behavior", ports=ports)
