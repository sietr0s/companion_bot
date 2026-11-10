"""Assemble module capabilities without sibling imports inside modules."""

from typing import Any

from fastapi import FastAPI

from src.composition.modules import MODULE_NAMES, load_modules
from src.core.application.host import create_host
from src.core.application.module import ModuleContext
from src.core.config import settings


def _needs_local_ai(names: tuple[str, ...], ports: dict[str, Any]) -> bool:
    return ("memory" in names and "memory_intelligence" not in ports) or (
        "behavior" in names and "chat_provider" not in ports
    )


def create_application(
    names: tuple[str, ...] = MODULE_NAMES,
    *,
    standalone: bool = False,
    ports: dict[str, Any] | None = None,
) -> FastAPI:
    modules = load_modules(names)
    provided = ports or {}
    local_ai = _needs_local_ai(names, provided)
    dependencies = (
        load_modules(("llm",)) if not settings.SAFE_MODE and "llm" not in names and local_ai else ()
    )

    def wire(context: ModuleContext) -> None:
        if context.safe_mode:
            return
        from src.composition.ai import get_chat_provider, get_memory_intelligence

        if "llm" in names or local_ai:
            from src.modules.llm.dependencies import reset_providers

            reset_providers()
        if "memory" in names and "memory_intelligence" not in context.services:
            context.services["memory_intelligence"] = get_memory_intelligence()
        if "behavior" in names and "chat_provider" not in context.services:
            context.services["chat_provider"] = get_chat_provider()

    return create_host(
        modules,
        standalone=standalone,
        ports=ports,
        wire_ports=wire,
        config_dependencies=dependencies,
    )


def create_service_app(name: str, *, ports: dict[str, Any] | None = None) -> FastAPI:
    return create_application((name,), standalone=True, ports=ports)
