"""One process owns one database and one bus, with explicit module lifecycles."""

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import AsyncExitStack, asynccontextmanager
from typing import TYPE_CHECKING, Any, cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.bus import configure_bus, create_bus
from src.core.application.module import ModuleContext, ModuleDefinition
from src.core.config import settings
from src.core.database import create_async_session, dispose_db, init_db
from src.core.exceptions import AppException

if TYPE_CHECKING:
    from sqlalchemy import Table

logger = logging.getLogger(__name__)


async def app_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, AppException):
        raise exc
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


async def health_check() -> dict[str, str]:
    return {"status": "ok"}


async def _drain(context: ModuleContext) -> None:
    transport = getattr(context.producer, "transport", None)
    if transport is not None:
        await asyncio.wait_for(transport.queue.join(), timeout=30)


async def _shutdown_modules(context: ModuleContext, modules: tuple[ModuleDefinition, ...]) -> None:
    # Stop ingress first. Kafka's consumer must stop before flushing local state;
    # its durable transport retains flushed events for downstream services.
    for module in reversed(modules):
        await module.quiesce(context)
    if settings.MESSAGE_BUS == "kafka" and not context.safe_mode:
        await context.consumer.stop()
    await _drain(context)
    # Declaration order places upstream batch flush before downstream background waits.
    for module in modules:
        await module.stop(context)
        await _drain(context)


async def _shutdown(context: ModuleContext, modules: tuple[ModuleDefinition, ...]) -> None:
    await asyncio.wait_for(_shutdown_modules(context, modules), timeout=60)


async def _load_configurations(
    app: FastAPI, context: ModuleContext, modules: tuple[ModuleDefinition, ...]
) -> None:
    tables = [cast("Table", model.__table__) for module in modules for model in module.models]
    await init_db(tables=tables)
    for module in modules:
        async with create_async_session() as session:
            snapshot = await module.configuration.load_snapshot(session)
        context.configs[module.name] = snapshot
        module.install_config(snapshot)
        setattr(app.state, module.name + "_config", snapshot)


def create_host(
    modules: tuple[ModuleDefinition, ...],
    *,
    standalone: bool = False,
    ports: dict[str, Any] | None = None,
    wire_ports: Callable[[ModuleContext], None] | None = None,
    config_dependencies: tuple[ModuleDefinition, ...] = (),
) -> FastAPI:
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    names = tuple(module.name for module in modules)
    if not names:
        raise ValueError("At least one module must be selected")
    group = f"{settings.KAFKA_GROUP_ID}.{names[0]}" if standalone else None
    producer, consumer = create_bus(group_id=group)
    configure_bus(producer, consumer)
    context = ModuleContext(producer, consumer, settings.SAFE_MODE, dict(ports or {}))

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if standalone and not settings.SAFE_MODE and settings.MESSAGE_BUS != "kafka":
            raise RuntimeError(
                "Standalone modules require MESSAGE_BUS=kafka; use SAFE_MODE=true for offline API"
            )
        context.services.clear()
        context.services.update(ports or {})
        context.configs.clear()
        async with AsyncExitStack() as cleanup:
            cleanup.push_async_callback(dispose_db)
            configured = (*config_dependencies, *modules)
            for module in configured:
                cleanup.callback(module.clear_config)
            await _load_configurations(app, context, configured)
            if wire_ports is not None:
                wire_ports(context)
            for module in modules:
                await module.prepare(context)
            cleanup.push_async_callback(producer.stop)
            await producer.start()
            cleanup.push_async_callback(consumer.stop)
            await consumer.start()
            cleanup.push_async_callback(_shutdown, context, modules)
            for module in modules:
                await module.start(context)
            logger.info("Modules started: %s; safe_mode=%s", names, settings.SAFE_MODE)
            yield

    app = FastAPI(title=settings.APP_TITLE, debug=settings.DEBUG, lifespan=lifespan)
    app.state.container = context
    app.state.modules = names
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_api_route("/health", health_check, methods=["GET"], tags=["Health"])
    for module in modules:
        app.include_router(module.router)
    return app
