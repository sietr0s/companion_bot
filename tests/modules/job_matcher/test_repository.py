"""
Тесты репозиториев модуля job_matcher.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.job_matcher.models import JobOffer, Subscription
from src.modules.job_matcher.repository import (
    JobOfferRepository,
    SubscriptionRepository,
)


class TestSubscriptionRepository:
    """Тесты SubscriptionRepository."""

    async def test_get_by_auth_id_found(self, db_session: AsyncSession):
        """Поиск подписки по auth_id."""
        auth_id = uuid.uuid4()
        sub = Subscription(auth_id=auth_id, is_active=True)
        db_session.add(sub)
        await db_session.commit()

        repo = SubscriptionRepository(model=Subscription)
        found = await repo.get_by_auth_id(db_session, auth_id)
        assert found is not None
        assert found.auth_id == auth_id

    async def test_get_by_auth_id_not_found(self, db_session: AsyncSession):
        """Поиск несуществующей подписки."""
        repo = SubscriptionRepository(model=Subscription)
        found = await repo.get_by_auth_id(db_session, uuid.uuid4())
        assert found is None

    async def test_find_matching_by_tags(self, db_session: AsyncSession):
        """Поиск подходящих подписок по тегам."""
        sub = Subscription(
            auth_id=uuid.uuid4(),
            is_active=True,
            keywords=["python", "backend"],
        )
        db_session.add(sub)
        await db_session.commit()

        repo = SubscriptionRepository(model=Subscription)
        matching = await repo.find_matching(db_session, tags=["python"])
        assert len(matching) == 1
        assert matching[0].auth_id == sub.auth_id

    async def test_find_matching_ignores_inactive(self, db_session: AsyncSession):
        """Поиск игнорирует неактивные подписки."""
        sub = Subscription(
            auth_id=uuid.uuid4(),
            is_active=False,
            keywords=["python"],
        )
        db_session.add(sub)
        await db_session.commit()

        repo = SubscriptionRepository(model=Subscription)
        matching = await repo.find_matching(db_session, tags=["python"])
        assert len(matching) == 0


class TestJobOfferRepository:
    """Тесты JobOfferRepository."""

    async def test_get_by_source_found(self, db_session: AsyncSession):
        """Поиск оффера по источнику."""
        offer = JobOffer(
            title="Python Developer",
            source_chat_id=100,
            source_message_id=200,
        )
        db_session.add(offer)
        await db_session.commit()

        repo = JobOfferRepository(model=JobOffer)
        found = await repo.get_by_source(db_session, source_chat_id=100, source_message_id=200)
        assert found is not None
        assert found.title == "Python Developer"

    async def test_get_by_source_not_found(self, db_session: AsyncSession):
        """Поиск несуществующего оффера."""
        repo = JobOfferRepository(model=JobOffer)
        found = await repo.get_by_source(db_session, source_chat_id=999, source_message_id=999)
        assert found is None
