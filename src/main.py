"""
Точка входа приложения.

Инициализирует шину сообщений (in-memory или Kafka),
TelegramClientManager, подключает роутеры модулей,
настраивает жизненный цикл.
Модули изолированы — связаны только через шину сообщений.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.bus import get_producer
from src.bus.in_memory.consumer import InMemoryConsumer
from src.bus.kafka.consumer import KafkaConsumerRouter
from src.core.bus_topics import BusTopics
from src.core.config import settings
from src.core.database import async_session_factory, init_db
from src.modules.telegram_clients.dependencies import get_telegram_client_service_factory, get_telegram_client_manager

# Настройка логирования приложения (INFO по умолчанию, переопределяется LOG_LEVEL)
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,
)

# Подавление шумных логов внешних библиотек
logging.getLogger("aiokafka").setLevel(logging.WARNING)

from src.core.exceptions import AppException
from src.core.seed import seed_admin
from src.modules.auth.routers import internal_router as auth_internal_router
from src.modules.auth.routers import public_router as auth_router
from src.modules.classifier.ai.category import (
    get_category_classifier,
)
from src.modules.classifier.handlers import (
    init_default_categories_on_startup,
)
from src.modules.classifier.handlers import (
    register_handlers as register_classifier_handlers,
)
from src.modules.classifier.routers import internal_router as classifier_internal_router
from src.modules.classifier.routers import public_router as classifier_router

# Модуль job_bot — шлюз Telegram
from src.modules.job_bot.bot import create_bot, create_bot_service, create_dispatcher
from src.modules.job_matcher.handlers import (
    register_handlers as register_job_matcher_handlers,
)
from src.modules.media.routers import internal_router as media_internal_router
from src.modules.media.routers import public_router as media_router
from src.modules.media.storage.local import LocalStorage
from src.modules.notifications.handlers import (
    register_handlers as register_notification_handlers,
)
from src.modules.notifications.routers import internal_router as notifications_internal_router
from src.modules.notifications.routers import public_router as notifications_router
from src.modules.telegram_clients.handlers import (
    register_handlers as register_tg_handlers,
)
from src.modules.telegram_clients.routers import internal_router as tg_internal_router
from src.modules.telegram_clients.routers import public_router as tg_router
from src.modules.users.handlers import register_handlers as register_users_handlers
from src.modules.users.routers import internal_router as users_internal_router
from src.modules.users.routers import public_router as users_router

logger = logging.getLogger(__name__)


client_manager = get_telegram_client_manager()
telegram_service = get_telegram_client_service_factory()
producer = get_producer()

# Регистрация обработчиков событий на шину.
register_users_handlers()
register_tg_handlers()
register_notification_handlers()
register_classifier_handlers()
register_job_matcher_handlers()


# Регистрация DLQ-обработчика (dead-letter queue для сообщений с ошибками)
@producer.subscribe(BusTopics.DLQ)
async def handle_dlq(message: dict) -> None:
    """
    Обработчик dead-letter queue.

    Логирует сообщения, которые не удалось обработать.
    В будущем может отправлять в отдельный топик Kafka
    или в систему мониторинга.
    """
    logger.warning(
        "DLQ: сообщение из топика '%s' не обработано. "
        "Ошибка: %s (%s). Обработчик: %s",
        message.get("original_topic"),
        message.get("error_detail"),
        message.get("error_type"),
        message.get("handler"),
    )


# Создание консьюмера с реестром подписчиков от продюсера
if settings.MESSAGE_BUS == "kafka":
    consumer = KafkaConsumerRouter(producer.get_subscribers())
else:
    consumer = InMemoryConsumer(producer.get_subscribers())


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Жизненный цикл приложения.
    """
    # Startup
    await init_db()
    await producer.start()
    await consumer.start()

    # Создаём admin-пользователя при старте
    async with async_session_factory() as session:
        await seed_admin(session)

    # Инициализация категорий по умолчанию
    await init_default_categories_on_startup()

    # Инициализация AI-модели классификатора (загрузка BART)
    classifier_model = get_category_classifier()
    await classifier_model.initialize()

    # Создаём папку для загрузок если LocalStorage
    if settings.MEDIA_STORAGE_PROVIDER == "local":
        LocalStorage().ensure_base_path()

    # Подключаем все ранее авторизованные Telegram-аккаунты
    async with async_session_factory() as session:
        await telegram_service.restore_tg_sessions(session)

    # Читаем непрочитанные сообщения для всех аккаунтов
    async with async_session_factory() as session:
        accounts = await telegram_service.get_active_accounts(session)
        for account in accounts:
            await telegram_service.read_unread_messages(session, account.id)

    # Запуск Telegram-бота
    bot = create_bot()
    bot_service = create_bot_service(bot)
    dp = create_dispatcher(producer, bot_service)

    if settings.TG_BOT_MODE == "webhook":
        # Webhook — регистрируем роут в FastAPI
        webhook_url = f"{settings.APP_URL}/webhook/bot"
        await bot.set_webhook(
            url=webhook_url,
            secret_token=settings.TG_BOT_WEBHOOK_SECRET,
        )
        logger.info("Бот запущен в режиме webhook: %s", webhook_url)
    else:
        # Polling — фоновая задача
        asyncio.create_task(dp.start_polling(bot))
        logger.info("Бот запущен в режиме polling")

    logger.info("Приложение запущено, шина: %s", settings.MESSAGE_BUS)

    yield

    # Shutdown
    await bot.session.close()
    await client_manager.stop_all()
    await consumer.stop()
    await producer.stop()
    logger.info("Приложение остановлено")


app = FastAPI(
    title=settings.APP_TITLE,
    debug=settings.DEBUG,
    lifespan=lifespan,
)


# Глобальный обработчик исключений приложения
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Единый формат ошибок для всех AppException."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )



@app.get("/health", tags=["Health"])
async def health_check():
    """Health check — без БД, без зависимостей."""
    return {"status": "ok"}


# Public API с версионированием /api/v1/ (префиксы в модулях)
app.include_router(auth_router, tags=["Auth"])
app.include_router(users_router, tags=["Users"])
app.include_router(notifications_router, tags=["Notifications"])
app.include_router(tg_router, tags=["Telegram Clients"])
app.include_router(media_router, tags=["Media"])
app.include_router(classifier_router, tags=["Classifier"])

# Internal API (без версионирования, для внутреннего использования)
app.include_router(auth_internal_router, prefix="/internal/auth", tags=["Internal"])
app.include_router(users_internal_router, prefix="/internal/users", tags=["Internal"])
app.include_router(
    notifications_internal_router, prefix="/internal/notifications", tags=["Internal"]
)
app.include_router(tg_internal_router, prefix="/internal/telegram", tags=["Internal"])
app.include_router(media_internal_router, prefix="/internal/media", tags=["Internal"])
app.include_router(classifier_internal_router, prefix="/internal/classifier", tags=["Internal"])
