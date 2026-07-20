"""Уведомления job_matcher о новых вакансиях."""

import uuid
from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.bus_topics import BusTopics
from src.modules.job_matcher.repository import JobOfferRepository, SubscriptionRepository
from src.modules.job_matcher.services import JobOfferService


async def test_notification_contains_full_saved_offer_text(
    db_session: AsyncSession,
) -> None:
    category_id = uuid.uuid4()
    auth_id = uuid.uuid4()
    full_text = "Python Developer\n\nПолное описание обязанностей и требований вакансии."
    offer_repository = JobOfferRepository()
    subscription_repository = SubscriptionRepository()
    bus = AsyncMock()
    service = JobOfferService(
        offer_repo=offer_repository,
        sub_repo=subscription_repository,
        bus=bus,
    )
    offer = await offer_repository.create(
        db_session,
        {
            "title": "Python Developer",
            "description": full_text,
            "source_chat_id": 1,
            "source_message_id": 2,
            "telegram_sender_id": 123456,
            "telegram_username": "vacancy_author",
            "telegram_first_name": "Иван",
            "telegram_last_name": "Иванов",
        },
    )
    await subscription_repository.create(
        db_session,
        {
            "auth_id": auth_id,
            "category_ids": [str(category_id)],
            "is_active": True,
        },
    )

    await service.handle_offer_classified(
        session=db_session,
        job_offer_id=offer.id,
        category_ids=[category_id],
    )

    bus.publish.assert_awaited_once_with(
        BusTopics.NOTIFICATION_SEND,
        {
            "auth_id": str(auth_id),
            "template_name": "job_offer",
            "channel": "telegram",
            "body": {
                "offer_text": full_text,
                "telegram_sender_id": 123456,
                "telegram_username": "vacancy_author",
                "telegram_first_name": "Иван",
                "telegram_last_name": "Иванов",
            },
        },
    )
