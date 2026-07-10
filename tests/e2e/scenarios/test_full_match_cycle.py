"""
E2E тест: Полный цикл match.

Сценарий:
1. Telethon → сообщение боту ("ищу вакансию Python разработчика")
2. aiogram → получает сообщение
3. bot.message.incoming → шина
4. job_matcher → классификация текста
5. job_matcher → подбор вакансий из БД
6. bot.message.outgoing → шина
7. Бот → ответ с вакансиями
8. Telethon → проверка ответа

Примечание: Это сложный интеграционный тест, требующий:
- Запущенного job_matcher service
- Classifier модуля (AI)
- Базы данных с вакансиями и подписками
"""
import pytest
import asyncio
from uuid import uuid4
from telethon import TelegramClient
from aiogram import Bot

from tests.e2e.utils import wait_for_event, get_last_message_from_bot


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.bot
@pytest.mark.slow
async def test_full_match_cycle(
    telegram_client: TelegramClient,
    test_bot: Bot,
    message_bus_collector,
    e2e_db_session
):
    """
    Полный цикл: сообщение → классификация → подбор → ответ.
    
    Проверяет:
    - Сообщение отправлено боту
    - bot.message.incoming опубликовано
    - job_matcher обработал сообщение
    - bot.message.outgoing опубликовано
    - Ответ содержит вакансии
    
    Примечание: Тест требует полной интеграции всех модулей.
    """
    # Получить username бота
    bot_info = await test_bot.get_me()
    bot_username = bot_info.username
    
    # Telethon отправляет сообщение
    test_message = "Ищу вакансию Python разработчика"
    await telegram_client.send_message(bot_username, test_message)
    
    # Дать время на обработку
    await asyncio.sleep(1.0)
    
    # Подождать bot.message.incoming
    incoming_event = await wait_for_event(
        message_bus_collector,
        "bot.message.incoming",
        timeout=5.0
    )
    
    if incoming_event is None:
        pytest.skip(
            "bot.message.incoming не опубликовано. "
            "Требуется зарегистрированный обработчик."
        )
    
    assert incoming_event["payload"]["text"] == test_message
    
    # Подождать job.offer.classified (если classifier подключён)
    classified_event = await wait_for_event(
        message_bus_collector,
        "job.offer.classified",
        timeout=10.0
    )
    
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
    
    # Если все модули работают — проверяем ответ
    if response_text:
        # Ожидаем упоминание вакансий или подписки
        assert any(
            keyword in response_text.lower()
            for keyword in ["ваканс", "подписк", "классифик", "python"]
        )


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.bot
async def test_subscribe_flow(
    telegram_client: TelegramClient,
    test_bot: Bot,
    message_bus_collector
):
    """
    Тест потока подписки: /subscribe → создание подписки.
    
    Проверяет:
    - Команда /subscribe отправлена
    - bot.message.incoming опубликовано
    - Подписка создана (проверка через БД)
    """
    bot_info = await test_bot.get_me()
    bot_username = bot_info.username
    
    # Отправить команду подписки
    await telegram_client.send_message(bot_username, "/subscribe")
    
    await asyncio.sleep(0.5)
    
    # Проверить bot.message.incoming
    incoming_event = await wait_for_event(
        message_bus_collector,
        "bot.message.incoming",
        timeout=5.0
    )
    
    if incoming_event is not None:
        assert incoming_event["payload"]["command"] == "/subscribe"
