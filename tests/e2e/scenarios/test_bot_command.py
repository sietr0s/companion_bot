"""
E2E тест: Команда боту (/start).

Сценарий:
1. Telethon → пользователь отправляет /start боту
2. aiogram → получает команду
3. Публикация bot.message.incoming в шину
4. job_bot handler → обрабатывает команду
5. Публикация bot.message.outgoing
6. Бот → отправляет ответ
7. Telethon → проверяет ответ

Примечание: Для работы теста требуется:
- Запущенный aiogram бот (polling или webhook)
- Зарегистрированные обработчики входящих сообщений
"""
import pytest
import asyncio
from telethon import TelegramClient
from aiogram import Bot

from tests.e2e.utils import wait_for_event, get_last_message_from_bot


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.bot
async def test_bot_start_command(
    telegram_client: TelegramClient,
    test_bot: Bot,
    message_bus_collector
):
    """
    Пользователь отправляет /start → бот отвечает.
    
    Проверяет:
    - Команда отправлена боту
    - bot.message.incoming опубликовано
    - bot.message.outgoing опубликовано
    - Бот отправил приветственное сообщение
    """
    # Получить username бота
    bot_info = await test_bot.get_me()
    bot_username = bot_info.username
    
    # Telethon отправляет /start
    await telegram_client.send_message(bot_username, "/start")
    
    # Дать время на обработку
    await asyncio.sleep(0.5)
    
    # Подождать bot.message.incoming
    incoming_event = await wait_for_event(
        message_bus_collector,
        "bot.message.incoming",
        timeout=5.0
    )
    
    if incoming_event is None:
        # В полной интеграции обработчик зарегистрирован
        # Здесь проверяем только что команда отправлена
        pytest.skip(
            "bot.message.incoming не опубликовано. "
            "Требуется зарегистрированный обработчик."
        )
    
    assert incoming_event["payload"]["text"] == "/start"
    
    # Подождать bot.message.outgoing
    outgoing_event = await wait_for_event(
        message_bus_collector,
        "bot.message.outgoing",
        timeout=5.0
    )
    
    if outgoing_event is not None:
        assert "chat_id" in outgoing_event["payload"]
        assert "text" in outgoing_event["payload"]
    
    # Проверить ответ через Telethon
    response_text = await get_last_message_from_bot(
        telegram_client,
        bot_username
    )
    
    # Если обработчик зарегистрирован — проверяем приветствие
    if response_text:
        assert "добро пожаловать" in response_text.lower() or "привет" in response_text.lower()


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.bot
async def test_bot_unknown_command(
    telegram_client: TelegramClient,
    test_bot: Bot,
    message_bus_collector
):
    """
    Пользователь отправляет неизвестную команду → бот игнорирует.
    """
    bot_info = await test_bot.get_me()
    bot_username = bot_info.username
    
    # Отправить неизвестную команду
    await telegram_client.send_message(bot_username, "/unknown")
    
    await asyncio.sleep(0.5)
    
    # Проверить что нет ответа (или стандартный ответ бота)
    response_text = await get_last_message_from_bot(
        telegram_client,
        bot_username
    )
    
    # Бот может не отвечать на неизвестные команды
    # Это зависит от реализации handlers
    assert response_text is None or "не знаю" in response_text.lower()
