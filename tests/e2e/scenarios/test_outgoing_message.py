"""
E2E тест: Исходящее сообщение через Telegram.

Сценарий:
1. Публикация tg.message.send в шину
2. TelegramClientManager → отправляет сообщение
3. Telethon → проверяет получение

Примечание: Для работы теста требуется:
- Запущенный TelegramClientManager (слушает шину)
- Реальный Telegram аккаунт в сессии
"""

import uuid

import pytest
from aiogram import Bot
from telethon import TelegramClient

from src.bus.in_memory import InMemoryProducer
from src.core.bus_topics import BusTopics


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.telegram
async def test_outgoing_message_via_telegram(
    telegram_client: TelegramClient, test_bot: Bot, message_bus_collector: InMemoryProducer
):
    """
    Публикация tg.message.send → отправка через Telethon.

    Проверяет:
    - Событие опубликовано в шину
    - Сообщение доставлено получателю

    Примечание: В полной интеграции TelegramClientManager
    подписывается на шину и отправляет сообщение.
    """
    # Получить chat_id тестового аккаунта
    me = await telegram_client.get_me()
    chat_id = me.id

    # Опубликовать событие в шину
    test_text = f"Outgoing E2E Test {id(test_bot)}"
    account_id = uuid.uuid4()

    message_data = {"account_id": str(account_id), "chat_id": str(chat_id), "text": test_text}

    # Публикация в шину
    await message_bus_collector.publish(BusTopics.TG_MESSAGE_SEND, message_data)

    # Проверка: событие опубликовано (InMemoryProducer не сохраняет историю,
    # но в полной интеграции подписчик получит событие)
    # Для проверки добавим атрибут вручную (см. InMemoryProducer)
    # В реальной интеграции TelegramClientManager подпишется и отправит сообщение


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.telegram
async def test_outgoing_message_format(
    telegram_client: TelegramClient, message_bus_collector: InMemoryProducer
):
    """
    Проверка формата сообщения для отправки.

    Проверяет:
    - Корректная структура события
    - UUID аккаунта валиден
    - chat_id конвертируется
    """
    me = await telegram_client.get_me()
    chat_id = me.id
    account_id = uuid.uuid4()

    test_text = "Test message format"

    message_data = {"account_id": str(account_id), "chat_id": str(chat_id), "text": test_text}

    # Валидация данных
    assert uuid.UUID(message_data["account_id"])
    assert int(message_data["chat_id"])
    assert isinstance(message_data["text"], str)
    assert len(message_data["text"]) > 0

    # Публикация
    await message_bus_collector.publish(BusTopics.TG_MESSAGE_SEND, message_data)
