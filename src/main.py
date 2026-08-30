"""Composition root приложения и фабрика FastAPI."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.bus import configure_bus
from src.core.bus_topics import BusTopics
from src.core.config import settings
from src.core.container import ApplicationContainer
from src.core.database import create_async_session, init_db
from src.core.exceptions import AppException
from src.core.seed import seed_admin
from src.modules.auth.routers import internal_router as auth_internal_router
from src.modules.auth.routers import public_router as auth_router
from src.modules.telegram_clients.dependencies import get_telegram_client_manager
from src.modules.telegram_clients.handlers import register_handlers as register_tg_handlers
from src.modules.telegram_clients.routers import internal_router as tg_internal_router
from src.modules.telegram_clients.routers import public_router as tg_router
from src.modules.users.handlers import register_handlers as register_users_handlers
from src.modules.users.routers import internal_router as users_internal_router
from src.modules.users.routers import public_router as users_router

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,
)
logging.getLogger("aiokafka").setLevel(logging.WARNING)


def _register_bus_handlers(container: ApplicationContainer) -> None:
    consumer = container.consumer

    register_users_handlers(consumer)
    register_tg_handlers(consumer, container.telegram_client_manager)
    register_notification_handlers(consumer)

    @consumer.subscribe(BusTopics.DLQ)
    async def handle_dlq(message: dict) -> None:
        logger.warning(
            "DLQ: сообщение из топика '%s' не обработано. "
            "Ошибка: %s (%s). Обработчик: %s",
            message.get("original_topic"),
            message.get("error_detail"),
            message.get("error_type"),
            message.get("handler"),
        )


def _create_lifespan(container: ApplicationContainer):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        producer = container.producer
        consumer = container.consumer
        client_manager = container.telegram_client_manager
        telegram_service = container.telegram_service

        bot = create_bot()
        bot_service = create_bot_service(bot)
        dispatcher = create_dispatcher(producer, consumer, bot_service)

        await init_db()
        await producer.start()
        await consumer.start()

        async with create_async_session() as session:
            await seed_admin(session, producer)

        if settings.MEDIA_STORAGE_PROVIDER == "local":
            LocalStorage().ensure_base_path()

        async with create_async_session() as session:
            await telegram_service.restore_tg_sessions(session)

        async with create_async_session() as session:
            accounts = await telegram_service.get_active_accounts(session)
            for account in accounts:
                await telegram_service.read_unread_messages(session, account.id)

        polling_task: asyncio.Task[None] | None = None
        if settings.TG_BOT_MODE == "webhook":
            webhook_url = f"{settings.APP_URL}/webhook/bot"
            await bot.set_webhook(
                url=webhook_url,
                secret_token=settings.TG_BOT_WEBHOOK_SECRET,
            )
            logger.info("Бот запущен в режиме webhook: %s", webhook_url)
        else:
            polling_task = asyncio.create_task(dispatcher.start_polling(bot))
            logger.info("Бот запущен в режиме polling")

        logger.info("Приложение запущено, шина: %s", settings.MESSAGE_BUS)

        yield

        if polling_task is not None:
            polling_task.cancel()
            with suppress(asyncio.CancelledError):
                await polling_task
        await bot.session.close()
        await client_manager.stop_all()
        await consumer.stop()
        await producer.stop()
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
    container = container or ApplicationContainer.create()
    configure_bus(container.producer, container.consumer)
    _register_bus_handlers(container)

    application = FastAPI(
        title=settings.APP_TITLE,
        debug=settings.DEBUG,
        lifespan=_create_lifespan(container),
    )
    application.state.container = container

    application.dependency_overrides[get_telegram_client_manager] = (
        lambda: container.telegram_client_manager
    )

    application.add_exception_handler(AppException, app_exception_handler)
    application.add_api_route("/health", health_check, methods=["GET"], tags=["Health"])

    application.include_router(auth_router)
    application.include_router(auth_internal_router)
    application.include_router(users_router)
    application.include_router(users_internal_router)
    application.include_router(tg_router)
    application.include_router(tg_internal_router)
    application.include_router(media_router)
    application.include_router(media_internal_router)

    return application


app = create_app()
