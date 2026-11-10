"""Composition root приложения и фабрика FastAPI."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from src.bus import configure_bus
from src.composition.container import ApplicationContainer
from src.composition.models import load_models
from src.core.config import settings
from src.core.database import create_async_session, dispose_db, init_db
from src.core.exceptions import AppException
from src.core.runtime import require_external_services
from src.modules.auth.routers import router as auth_router
from src.modules.auth.seed import seed_admin
from src.modules.batching.config.service import BatchingConfigService
from src.modules.batching.handlers import register_handlers as register_batching_handlers
from src.modules.batching.routers import router as batching_router
from src.modules.behavior.handlers import register_handlers as register_behavior_handlers
from src.modules.instagram_clients.dependencies import configure_instagram_client_manager
from src.modules.instagram_clients.handlers import register_handlers as register_ig_handlers
from src.modules.instagram_clients.routers import router as ig_router
from src.modules.llm.handlers import register_handlers as register_llm_handlers
from src.modules.memory.handlers import register_handlers as register_memory_handlers
from src.modules.memory.routers import router as memory_router
from src.modules.orchestrator.handlers import register_handlers as register_orchestrator_handlers
from src.modules.stt.handlers import register_handlers as register_stt_handlers
from src.modules.telegram_clients.dependencies import configure_telegram_client_manager
from src.modules.telegram_clients.handlers import register_handlers as register_tg_handlers
from src.modules.telegram_clients.routers import router as tg_router
from src.modules.tts.handlers import register_handlers as register_tts_handlers
from src.modules.users.handlers import register_handlers as register_users_handlers
from src.modules.users.routers import router as users_router

if TYPE_CHECKING:
    from src.modules.batching.config import BatchingSettings

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,
)
logging.getLogger("aiokafka").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.orm").setLevel(logging.WARNING)


def _register_bus_handlers(
    container: ApplicationContainer, batching_config: BatchingSettings
) -> None:
    consumer = container.consumer
    producer = container.producer

    register_users_handlers(consumer, producer)
    if settings.SAFE_MODE:
        return
    register_tg_handlers(consumer, container.telegram_client_manager, producer)
    register_ig_handlers(consumer, container.instagram_client_manager, producer)
    register_batching_handlers(consumer, producer, batching_config)
    register_memory_handlers(consumer, producer)
    register_behavior_handlers(consumer, producer)
    register_llm_handlers(consumer, producer)
    register_stt_handlers(consumer, producer, container.telegram_client_manager)
    register_tts_handlers(consumer, producer)
    register_orchestrator_handlers(consumer, producer)


async def _restore_integrations(container: ApplicationContainer) -> None:
    async with create_async_session() as session:
        await container.telegram_service.restore_tg_sessions(session)

    async with create_async_session() as session:
        accounts = await container.telegram_service.get_active_accounts(session)
        for account in accounts:
            await container.telegram_service.read_unread_messages(session, account.id)

    async with create_async_session() as session:
        await container.instagram_service.restore_sessions(session)


def _create_lifespan(container: ApplicationContainer):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        producer = container.producer
        consumer = container.consumer
        client_manager = container.telegram_client_manager
        ig_manager = container.instagram_client_manager

        try:
            await init_db()
            async with create_async_session() as session:
                batching_config = await BatchingConfigService().load_snapshot(session)
        except Exception:
            await dispose_db()
            raise
        app.state.batching_config = batching_config
        _register_bus_handlers(container, batching_config)
        from src.modules.llm.dependencies import warmup_heavy_models
        from src.modules.stt.dependencies import warmup_stt

        if not settings.SAFE_MODE:
            await warmup_heavy_models()
            await warmup_stt()
        await producer.start()
        await consumer.start()

        async with create_async_session() as session:
            await seed_admin(session, producer)

        if not settings.SAFE_MODE:
            await _restore_integrations(container)

        logger.info("Приложение запущено, safe_mode=%s", settings.SAFE_MODE)

        yield

        await ig_manager.stop_all()
        await client_manager.stop_all()
        await consumer.stop()
        await producer.stop()
        await dispose_db()
        logger.info("Приложение остановлено")

    return lifespan


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


async def health_check() -> dict[str, str]:
    return {"status": "ok"}


def create_app(container: ApplicationContainer | None = None) -> FastAPI:
    """Создать изолированный экземпляр приложения."""
    load_models()
    container = container or ApplicationContainer.create()
    configure_bus(container.producer, container.consumer)
    configure_telegram_client_manager(container.telegram_client_manager)
    configure_instagram_client_manager(container.instagram_client_manager)

    application = FastAPI(
        title=settings.APP_TITLE,
        debug=settings.DEBUG,
        lifespan=_create_lifespan(container),
    )
    application.state.container = container

    application.add_exception_handler(AppException, app_exception_handler)
    application.add_api_route("/health", health_check, methods=["GET"], tags=["Health"])

    application.include_router(auth_router)
    application.include_router(users_router)
    integration_policy = [Depends(require_external_services)]
    application.include_router(tg_router, dependencies=integration_policy)
    application.include_router(ig_router, dependencies=integration_policy)
    application.include_router(memory_router)
    application.include_router(batching_router)

    return application


app = create_app()
