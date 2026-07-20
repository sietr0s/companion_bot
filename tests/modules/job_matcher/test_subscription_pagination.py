"""Тесты постраничного выбора категории подписки."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.bus_topics import BusTopics
from src.modules.auth.repository import AuthRepository
from src.modules.classifier.repository import CategoryRepository
from src.modules.job_matcher.repository import SubscriptionRepository
from src.modules.job_matcher.services import SubscriptionService
from tests.conftest import MockBus


async def _create_categories(session: AsyncSession, count: int = 12) -> None:
    repository = CategoryRepository()
    for number in range(1, count + 1):
        await repository.create(
            session,
            {
                "name": f"Category {number:02d}",
                "slug": f"category-{number:02d}",
                "is_active": True,
            },
        )


async def test_subscription_categories_are_paginated_by_five(
    db_session: AsyncSession,
):
    telegram_id = 303486120
    await AuthRepository().create(
        db_session,
        {
            "identifier": f"tg_{telegram_id}",
            "identifier_type": "telegram",
            "hashed_password": "hashed",
        },
    )
    await _create_categories(db_session)
    bus = MockBus()
    service = SubscriptionService(
        repository=SubscriptionRepository(),
        bus=bus,
    )

    await service.handle_subscribe(
        session=db_session,
        chat_id=telegram_id,
        telegram_id=telegram_id,
    )

    topic, first_page = bus.published[-1]
    assert topic == BusTopics.BOT_MESSAGE_OUTGOING
    assert "Страница 1 из 3" in first_page["text"]
    assert len(first_page["keyboard"]["inline_keyboard"]) == 6
    assert first_page["keyboard"]["inline_keyboard"][0][0]["text"] == "Category 01"
    assert first_page["keyboard"]["inline_keyboard"][-1] == [
        {"text": "← Назад", "callback_data": "subscribe_page:noop"},
        {"text": "Вперёд →", "callback_data": "subscribe_page:1"},
    ]

    await service.handle_subscription_page(
        session=db_session,
        chat_id=telegram_id,
        message_id=55,
        page=1,
    )

    topic, middle_page = bus.published[-1]
    assert topic == BusTopics.BOT_MESSAGE_EDIT
    assert middle_page["message_id"] == 55
    assert "Страница 2 из 3" in middle_page["text"]
    assert len(middle_page["keyboard"]["inline_keyboard"]) == 6
    assert middle_page["keyboard"]["inline_keyboard"][0][0]["text"] == "Category 06"
    assert middle_page["keyboard"]["inline_keyboard"][-1] == [
        {"text": "← Назад", "callback_data": "subscribe_page:0"},
        {"text": "Вперёд →", "callback_data": "subscribe_page:2"},
    ]

    await service.handle_subscription_page(
        session=db_session,
        chat_id=telegram_id,
        message_id=55,
        page=2,
    )

    _, last_page = bus.published[-1]
    assert "Страница 3 из 3" in last_page["text"]
    assert len(last_page["keyboard"]["inline_keyboard"]) == 3
    assert last_page["keyboard"]["inline_keyboard"][0][0]["text"] == "Category 11"
    assert last_page["keyboard"]["inline_keyboard"][-1] == [
        {"text": "← Назад", "callback_data": "subscribe_page:1"},
        {"text": "Вперёд →", "callback_data": "subscribe_page:noop"},
    ]
