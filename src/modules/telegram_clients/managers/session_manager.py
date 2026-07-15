"""
Менеджер сессий Telegram-клиентов (stateless).

Отвечает за:
- Подключение и отключение аккаунтов
- Создание и настройка TelegramClient
- Управление session-файлами
- Остановка всех клиентов
- Регистрация обработчиков входящих сообщений

Не хранит состояние — клиенты и сервис живу в TelegramClientManager (фасад).
"""

import logging
import os
import uuid
from typing import Any

from telethon import TelegramClient, events

from src.core.config import settings
from src.core.database import async_session_factory

logger = logging.getLogger(__name__)


async def get_session_path(client_manager: Any, account_id: uuid.UUID) -> str:
    """Формирует путь к session-файлу."""
    session_dir = settings.TG_SESSION_DIR
    os.makedirs(session_dir, exist_ok=True)
    return os.path.join(session_dir, str(account_id))


async def create_client(session_path: str) -> TelegramClient:
    """Создаёт экземпляр TelegramClient."""
    logger.debug("TG_API_ID: %s", settings.TG_API_ID)
    logger.debug("TG_API_HASH: %s", settings.TG_API_HASH)
    return TelegramClient(
        session_path,
        settings.TG_API_ID,
        settings.TG_API_HASH,
        app_version=settings.TG_APP_VERSION,
        system_version=settings.TG_SYSTEM_VERSION,
        device_model=settings.TG_DEVICE_MODEL,
    )


async def connect_account(client_manager: Any, account_id: uuid.UUID) -> None:
    """
    Подключить аккаунт по существующей сессии.

    Используется при старте приложения для восстановления подключений.
    """
    session_path = get_session_path(client_manager, account_id)
    client = create_client(session_path)
    await client.connect()

    # Проверяем, авторизован ли клиент
    if not await client.is_user_authorized():
        await client.disconnect()
        logger.warning("Сессия аккаунта %s не авторизована", account_id)
        return

    client_manager.set_client(account_id, client)
    register_message_handler(client_manager, account_id, client)
    logger.info("Аккаунт %s подключён", account_id)


async def disconnect_account(client_manager: Any, account_id: uuid.UUID) -> None:
    """Отключить аккаунт и удалить клиент из памяти."""
    client = client_manager.remove_client(account_id)
    if client:
        await client.disconnect()
        logger.info("Аккаунт %s отключён", account_id)


async def stop_all(client_manager: Any) -> None:
    """Отключить все клиенты при остановке приложения."""
    for account_id in list(client_manager.get_all_client_ids()):
        await disconnect_account(client_manager, account_id)


def register_message_handler(
    client_manager: Any, account_id: uuid.UUID, client: TelegramClient,
) -> None:
    """Регистрирует обработчик входящих сообщений для клиента."""

    @client.on(events.NewMessage)
    async def on_new_message(event: events.NewMessage.Event) -> None:
        """
        Обработать входящее сообщение.

        Делегирует обработку в сервис.
        """
        if client_manager.get_service() is None:
            logger.error("Сервис не установлен для обработки сообщений")
            return

        async with async_session_factory() as session:
            service = client_manager.get_service()
            if service is None:
                return
            await service.handle_incoming_message(
                session=session,
                client=client,
                account_id=account_id,
                event=event,
            )
