"""
Тесты репозиториев модуля job_matcher.
"""

import uuid

from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.job_matcher.models import JobOffer, Subscription
from src.modules.job_matcher.repository import (
    JobOfferRepository,
    SubscriptionRepository,
    _json_contains,
)


def test_postgresql_json_contains_casts_json_to_jsonb() -> None:
    """PostgreSQL must compare JSONB with a JSONB array, not JSON with varchar."""

    class BindStub:
        dialect = postgresql.dialect()

    class SessionStub:
        bind = BindStub()

    category_id = str(uuid.uuid4())
    expression = _json_contains(
        SessionStub(),
        Subscription.category_ids,
        category_id,
    )
    compiled = expression.compile(dialect=postgresql.dialect())

    assert "CAST(subscriptions.category_ids AS JSONB)" in str(compiled)
    assert "@>" in str(compiled)
    assert "::JSONB" in str(compiled)
    assert list(compiled.params.values()) == [[category_id]]


class TestSubscriptionRepository:
    """Тесты SubscriptionRepository."""

    async def test_get_by_auth_id_found(self, db_session: AsyncSession):
        """Поиск подписки по auth_id."""
        auth_id = uuid.uuid4()
        sub = Subscription(auth_id=auth_id, is_active=True)
        db_session.add(sub)
        await db_session.commit()

        repo = SubscriptionRepository()
        found = await repo.get_by_auth_id(db_session, auth_id)
        assert found is not None
        assert found.auth_id == auth_id

    async def test_get_by_auth_id_not_found(self, db_session: AsyncSession):
        """Поиск несуществующей подписки."""
        repo = SubscriptionRepository()
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

        repo = SubscriptionRepository()
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

        repo = SubscriptionRepository()
        matching = await repo.find_matching(db_session, tags=["python"])
        assert len(matching) == 0

    async def test_find_matching_by_category_ids(self, db_session: AsyncSession):
        """Поиск подходящих подписок по пересечению категорий."""
        cat_a = str(uuid.uuid4())
        cat_b = str(uuid.uuid4())
        cat_c = str(uuid.uuid4())

        sub1 = Subscription(
            auth_id=uuid.uuid4(),
            is_active=True,
            category_ids=[cat_a, cat_b],
        )
        sub2 = Subscription(
            auth_id=uuid.uuid4(),
            is_active=True,
            category_ids=[cat_c],
        )
        db_session.add_all([sub1, sub2])
        await db_session.commit()

        repo = SubscriptionRepository()

        # Ищем по cat_a — должна найтись sub1
        matching = await repo.find_matching(
            db_session,
            category_ids=[uuid.UUID(cat_a)],
        )
        assert len(matching) == 1
        assert matching[0].id == sub1.id

        # Ищем по cat_c — должна найтись sub2
        matching = await repo.find_matching(
            db_session,
            category_ids=[uuid.UUID(cat_c)],
        )
        assert len(matching) == 1
        assert matching[0].id == sub2.id

        # Ищем по cat_a и cat_c — должны найтись обе
        matching = await repo.find_matching(
            db_session,
            category_ids=[uuid.UUID(cat_a), uuid.UUID(cat_c)],
        )
        assert len(matching) == 2

    async def test_category_subscription_matches_offer_with_tags(
        self,
        db_session: AsyncSession,
    ):
        """Отсутствие keywords не блокирует матчинг выбранной категории."""
        category_id = str(uuid.uuid4())
        sub = Subscription(
            auth_id=uuid.uuid4(),
            is_active=True,
            category_ids=[category_id],
            keywords=None,
        )
        db_session.add(sub)
        await db_session.commit()

        matching = await SubscriptionRepository().find_matching(
            db_session,
            category_ids=[uuid.UUID(category_id)],
            tags=["python", "backend"],
        )

        assert [item.id for item in matching] == [sub.id]

    async def test_find_matching_by_salary(self, db_session: AsyncSession):
        """Поиск подходящих подписок по зарплате."""
        sub1 = Subscription(
            auth_id=uuid.uuid4(),
            is_active=True,
            min_salary=100_000,
            max_salary=200_000,
        )
        sub2 = Subscription(
            auth_id=uuid.uuid4(),
            is_active=True,
            min_salary=150_000,
            max_salary=300_000,
        )
        sub3 = Subscription(
            auth_id=uuid.uuid4(),
            is_active=True,
            min_salary=None,
            max_salary=None,
        )
        db_session.add_all([sub1, sub2, sub3])
        await db_session.commit()

        repo = SubscriptionRepository()

        # Оффер с зарплатой 120_000–180_000
        # Все три подписки подходят:
        # - sub1 (100-200) — пересечение с 120-180
        # - sub2 (150-300) — пересечение с 120-180
        # - sub3 (без ограничений) — подходит всегда
        matching = await repo.find_matching(
            db_session,
            salary_min=120_000,
            salary_max=180_000,
        )
        assert len(matching) == 3

    async def test_find_matching_by_location(self, db_session: AsyncSession):
        """Поиск подходящих подписок по локации."""
        sub1 = Subscription(
            auth_id=uuid.uuid4(),
            is_active=True,
            locations=["Moscow", "SPb"],
        )
        sub2 = Subscription(
            auth_id=uuid.uuid4(),
            is_active=True,
            locations=["Kazan"],
        )
        sub3 = Subscription(
            auth_id=uuid.uuid4(),
            is_active=True,
            locations=None,
        )
        db_session.add_all([sub1, sub2, sub3])
        await db_session.commit()

        repo = SubscriptionRepository()

        # Ищем по Moscow
        matching = await repo.find_matching(db_session, location="Moscow")
        assert len(matching) == 2  # sub1 (Moscow) и sub3 (без ограничений)
        assert sub1 in matching
        assert sub3 in matching

    async def test_find_matching_all_filters(self, db_session: AsyncSession):
        """Поиск подходящих подписок со всеми фильтрами одновременно."""
        cat_a = str(uuid.uuid4())

        sub1 = Subscription(
            auth_id=uuid.uuid4(),
            is_active=True,
            category_ids=[cat_a],
            keywords=["python", "backend"],
            min_salary=100_000,
            max_salary=200_000,
            locations=["Moscow"],
        )
        sub2 = Subscription(
            auth_id=uuid.uuid4(),
            is_active=True,
            category_ids=[cat_a],
            keywords=["python"],
            min_salary=150_000,
            max_salary=300_000,
            locations=["SPb"],
        )
        db_session.add_all([sub1, sub2])
        await db_session.commit()

        repo = SubscriptionRepository()

        # Ищем оффер: категория A, тег python, зарплата 120_000, локация Moscow
        matching = await repo.find_matching(
            db_session,
            category_ids=[uuid.UUID(cat_a)],
            tags=["python"],
            salary_min=120_000,
            location="Moscow",
        )
        assert len(matching) == 1
        assert matching[0].id == sub1.id

    async def test_find_matching_empty_category_ids(self, db_session: AsyncSession):
        """Поиск без category_ids возвращает все активные подписки."""
        sub1 = Subscription(auth_id=uuid.uuid4(), is_active=True)
        sub2 = Subscription(auth_id=uuid.uuid4(), is_active=True)
        sub3 = Subscription(auth_id=uuid.uuid4(), is_active=False)
        db_session.add_all([sub1, sub2, sub3])
        await db_session.commit()

        repo = SubscriptionRepository()

        # Без фильтров — только активные
        matching = await repo.find_matching(db_session)
        assert len(matching) == 2
        assert sub1 in matching
        assert sub2 in matching


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

        repo = JobOfferRepository()
        found = await repo.get_by_source(db_session, source_chat_id=100, source_message_id=200)
        assert found is not None
        assert found.title == "Python Developer"

    async def test_get_by_source_not_found(self, db_session: AsyncSession):
        """Поиск несуществующего оффера."""
        repo = JobOfferRepository()
        found = await repo.get_by_source(db_session, source_chat_id=999, source_message_id=999)
        assert found is None
