"""
Точка входа приложения.

Инициализирует шину сообщений (in-memory или Kafka),
TelegramClientManager, подключает роутеры модулей,
настраивает жизненный цикл.
Модули изолированы — связаны только через шину сообщений.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from functools import partial
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.base.model import Base
from src.bus.in_memory.consumer import InMemoryConsumer
from src.bus.in_memory.producer import InMemoryProducer
from src.bus.kafka.consumer import KafkaConsumerRouter
from src.bus.kafka.producer import KafkaProducerBus
from src.core.bus_topics import BusTopics
from src.core.config import settings
from src.core.database import async_session_factory, engine

# Настройка логирования приложения (INFO по умолчанию, переопределяется LOG_LEVEL)
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,
)

# Подавление шумных логов внешних библиотек
logging.getLogger("aiokafka").setLevel(logging.WARNING)

from src.core.exceptions import AppException
from src.modules.auth.seed import seed_admin
from src.core.telegram_manager import create_telegram_client_manager
from src.modules.auth.routers import internal_router as auth_internal_router
from src.modules.auth.routers import public_router as auth_router
from src.modules.classifier.dependencies import get_classifier_service_factory
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
from src.modules.job_matcher.dependencies import get_job_matcher_service_factory
from src.modules.job_matcher.handlers import (
    register_handlers as register_job_matcher_handlers,
)
from src.modules.media.routers import internal_router as media_internal_router
from src.modules.media.routers import public_router as media_router
from src.modules.notifications.dependencies import get_notification_service_factory
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
from src.modules.users.handlers import register_handlers
from src.modules.users.routers import internal_router as users_internal_router
from src.modules.users.routers import public_router as users_router

logger = logging.getLogger(__name__)

# Выбор реализации шины сообщений на основе конфигурации.
if settings.MESSAGE_BUS == "kafka":
    producer = KafkaProducerBus()
else:
    producer = InMemoryProducer()

# TelegramClientManager — singleton для управления Telethon-клиентами.
# Инициализируется без параметров, сервис устанавливается позже
client_manager = create_telegram_client_manager()

# Регистрация обработчиков событий на шину.
register_handlers(producer)
# Передаём client_manager явно — он не в DI-контейнере
register_tg_handlers(producer, client_manager)

# Регистрация обработчиков notifications
register_notification_handlers(producer, get_notification_service_factory)

# Регистрация обработчиков classifier (AI-классификация текстов)
register_classifier_handlers(
    producer,
    partial(get_classifier_service_factory, bus=producer),
)

# Регистрация всех обработчиков job_matcher
register_job_matcher_handlers(
    producer,
    partial(get_job_matcher_service_factory, bus=producer),
)

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

    Startup:
    1. Запуск шины сообщений (продюсер + консьюмер)
    2. Создание таблиц в БД (при необходимости)
    3. Подключение Telegram-аккаунтов из БД

    Shutdown:
    1. Отключение Telegram-клиентов
    2. Остановка консьюмера
    3. Остановка продюсера
    """
    # Startup
    await producer.start()
    await consumer.start()

    # Создаём таблицы только в разработке (в проде — через Alembic миграции)
    if settings.CREATE_TABLES_ON_STARTUP:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Таблицы БД созданы (режим разработки)")

    # Создаём admin-пользователя при старте
    async with async_session_factory() as session:
        await seed_admin(session, producer)

    # Инициализация категорий по умолчанию
    await init_default_categories_on_startup()

    # Создаём папку для загрузок если LocalStorage
    if settings.MEDIA_STORAGE_PROVIDER == "local":
        from src.modules.media.storage.local import LocalStorage

        LocalStorage().ensure_base_path()

    # Создаём сервис и устанавливаем в менеджер для обработки входящих сообщений
    from src.modules.telegram_clients.repository import (
        TelegramAccountRepository,
        TelegramChatStateRepository,
        TelegramSettingsRepository,
    )
    from src.modules.telegram_clients.service import TelegramClientService

    telegram_service = TelegramClientService(
        repository=TelegramAccountRepository(),
        message_bus=producer,
        client_manager=client_manager,
        settings_repository=TelegramSettingsRepository(),
        chat_state_repository=TelegramChatStateRepository(),
    )
    client_manager.set_service(telegram_service)

    # Подключаем все ранее авторизованные Telegram-аккаунты
    await _restore_tg_sessions()

    # Читаем непрочитанные сообщения для всех аккаунтов
    await _read_unread_telegram_messages(telegram_service)

    # Запуск Telegram-бота (если настроен)
    if settings.TG_BOT_TOKEN:
        bot = create_bot(settings.TG_BOT_TOKEN)
        bot_service = create_bot_service(bot)

        # Создание диспетчера и регистрация обработчиков
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
    if settings.TG_BOT_TOKEN:
        await bot.session.close()

    await client_manager.stop_all()
    await consumer.stop()
    await producer.stop()
    logger.info("Приложение остановлено")


async def _restore_tg_sessions() -> None:
    """Восстановление подключений Telegram-аккаунтов при старте."""
    from sqlalchemy import select

    from src.core.database import async_session_factory
    from src.modules.telegram_clients.models import TelegramAccount

    async with async_session_factory() as session:
        stmt = select(TelegramAccount).where(TelegramAccount.is_connected.is_(True))
        result = await session.execute(stmt)
        accounts = result.scalars().all()

    for account in accounts:
        try:
            await client_manager.connect_account(account.id)
        except (ConnectionError, TimeoutError) as e:
            logger.error("Ошибка подключения Telegram для аккаунта %s: %s", account.id, e)
        except Exception as e:
            logger.exception("Неожиданная ошибка при подключении Telegram-аккаунта %s: %s", account.id, e)


async def _read_unread_telegram_messages(telegram_service: Any) -> None:
    """Чтение непрочитанных сообщений для всех подключённых аккаунтов."""
    from sqlalchemy import select

    from src.core.database import async_session_factory
    from src.modules.telegram_clients.models import TelegramAccount

    async with async_session_factory() as session:
        # Получаем все подключённые аккаунты
        stmt = select(TelegramAccount).where(TelegramAccount.is_connected.is_(True))
        result = await session.execute(stmt)
        accounts = result.scalars().all()

        if not accounts:
            logger.info("Нет подключённых Telegram-аккаунтов для чтения сообщений")
            return

        for account in accounts:
            count = await telegram_service.read_unread_messages(
                session=session,
                account_id=account.id,
            )

            logger.info(
                "Аккаунт %s: прочитано %d непрочитанных сообщений",
                account.id,
                count,
            )


# Создание FastAPI-приложения
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


# Подключение роутеров модулей.
# Каждый модуль — независимый «микросервис» с собственным префиксом.
# Public API: /api/v1/public/{module}, Internal API: /internal/{module}


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
