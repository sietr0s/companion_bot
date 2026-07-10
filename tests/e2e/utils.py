"""
E2E тесты ms_starter — вспомогательные утилиты.
"""
import asyncio
import logging
from typing import Any, Dict, Optional
from telethon import TelegramClient
from telethon.tl.types import Dialog

logger = logging.getLogger(__name__)


async def wait_for_event(
    bus_collector: Any,
    topic: str,
    timeout: float = 5.0,
    poll_interval: float = 0.1
) -> Optional[Dict[str, Any]]:
    """
    Ждать события из шины с таймаутом.

    Args:
        bus_collector: InMemoryProducer или другой collector
        topic: Название топика (например, "tg.message.received")
        timeout: Таймаут в секундах
        poll_interval: Интервал опроса в секундах

    Returns:
        Событие или None если таймаут
    """
    loop = asyncio.get_event_loop()
    start_time = loop.time()

    while (loop.time() - start_time) < timeout:
        # Проверить историю событий (если есть)
        if hasattr(bus_collector, 'events'):
            for event in bus_collector.events:
                if event.get("topic") == topic:
                    return event

        await asyncio.sleep(poll_interval)

    return None


async def _get_bot_dialog(
    telethon_client: TelegramClient,
    bot_username: str
) -> Optional[Dialog]:
    """
    Внутренняя функция: найти диалог с ботом.

    Args:
        telethon_client: Telethon клиент
        bot_username: Username бота (без @)

    Returns:
        Dialog или None если не найден
    """
    try:
        dialog = await telethon_client.get_dialogs()
        
        for d in dialog:
            if hasattr(d, 'user') and d.user.username == bot_username:
                return d
        
        logger.warning("Диалог с ботом @%s не найден", bot_username)
        return None
    except Exception as e:
        logger.error("Ошибка при поиске диалога с ботом %s: %s", bot_username, e)
        return None


async def assert_bot_response(
    telethon_client: TelegramClient,
    bot_username: str,
    expected_text: Optional[str] = None,
    timeout: float = 5.0
) -> bool:
    """
    Проверить ответ от бота через Telethon.

    Args:
        telethon_client: Telethon клиент
        bot_username: Username бота (без @)
        expected_text: Ожидаемый текст (если None, проверяет наличие любого ответа)
        timeout: Таймаут в секундах

    Returns:
        True если ответ получен и совпадает
    """
    bot_dialog = await _get_bot_dialog(telethon_client, bot_username)
    
    if not bot_dialog:
        return False

    try:
        messages = await telethon_client.get_messages(bot_dialog, limit=1)
        
        if not messages:
            return False

        last_message = messages[0]

        if expected_text is None:
            return True

        return last_message.text == expected_text
    except Exception as e:
        logger.error("Ошибка при получении сообщений от бота: %s", e)
        return False


async def get_last_message_from_bot(
    telethon_client: TelegramClient,
    bot_username: str
) -> Optional[str]:
    """
    Получить последнее сообщение от бота.

    Args:
        telethon_client: Telethon клиент
        bot_username: Username бота (без @)

    Returns:
        Текст сообщения или None
    """
    bot_dialog = await _get_bot_dialog(telethon_client, bot_username)
    
    if not bot_dialog:
        return None

    try:
        messages = await telethon_client.get_messages(bot_dialog, limit=1)
        
        if not messages:
            return None

        return messages[0].text
    except Exception as e:
        logger.error("Ошибка при получении сообщения от бота: %s", e)
        return None
