"""memory composition and standalone application factory."""

from typing import Any

from fastapi import FastAPI

from src.core.application.module import ModuleContext, ModuleDefinition
from src.modules.memory.config import binding
from src.modules.memory.config.model import MemoryConfigModel
from src.modules.memory.config.service import MemoryConfigService
from src.modules.memory.dependencies import build_memory_service
from src.modules.memory.handlers import register_handlers
from src.modules.memory.models import (
    Conversation,
    Message,
    MessageBatch,
    SummaryState,
    VectorRecord,
)
from src.modules.memory.routers import router


async def prepare(context: ModuleContext) -> None:
    if not context.safe_mode:
        intelligence = context.services.get("memory_intelligence")
        if intelligence is None:
            raise RuntimeError("Memory requires a MemoryIntelligence port from composition")
        register_handlers(
            context.consumer,
            context.producer,
            service=build_memory_service(context.producer, intelligence),
        )


def get_module() -> ModuleDefinition:
    return ModuleDefinition(
        name="memory",
        router=router,
        models=(
            Conversation,
            Message,
            MessageBatch,
            SummaryState,
            VectorRecord,
            MemoryConfigModel,
        ),
        configuration=MemoryConfigService(),
        install_config=binding.install,
        clear_config=binding.clear,
        prepare=prepare,
    )


def create_app(*, ports: dict[str, Any] | None = None) -> FastAPI:
    """Run this module only; shared infrastructure is owned by the host."""
    from src.composition.application import create_service_app

    return create_service_app("memory", ports=ports)
