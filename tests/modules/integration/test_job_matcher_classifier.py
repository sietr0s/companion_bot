"""
Интеграционные тесты взаимодействия job_matcher и classifier.

Проверяют архитектуру взаимодействия:
1. JobOffer сохраняется в БД
2. Отправляется на классификацию
3. Результат обновляет JobOffer

AI-модель может быть заглушкой — тестируем только архитектуру.
"""

import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bus.in_memory.producer import InMemoryProducer
from src.core.bus_topics import BusTopics
from src.modules.classifier.repository import CategoryRepository, ClassificationLogRepository
from src.modules.classifier.service import ClassifierService
from src.modules.job_matcher.models import JobOffer
from src.modules.job_matcher.repository import JobOfferRepository
from src.modules.job_matcher.service import JobMatcherService
from tests.conftest import MockBus


class MockCategoryClassifier:
    """Заглушка классификатора категорий для тестов."""

    async def classify(self, text: str, labels: list[dict]) -> MagicMock:
        """Возвращает фиксированный результат классификации."""
        result = MagicMock()
        # Возвращаем все категории с разными confidence
        from unittest.mock import Mock

        cat1 = Mock()
        cat1.id = uuid.uuid4()
        cat1.slug = labels[0]["slug"] if labels else "backend"
        cat1.name = labels[0]["name"] if labels else "Backend"
        cat1.confidence = 0.9

        cat2 = Mock()
        cat2.id = uuid.uuid4()
        cat2.slug = labels[1]["slug"] if len(labels) > 1 else "frontend"
        cat2.name = labels[1]["name"] if len(labels) > 1 else "Frontend"
        cat2.confidence = 0.7

        result.categories = [cat1, cat2]
        return result


class MockEntityExtractor:
    """Заглушка извлечения сущностей для тестов."""

    async def extract(self, text: str) -> MagicMock:
        """Возвращает фиксированные сущности."""
        result = MagicMock()
        result.entities = {
            "skills": ["Python", "Django"],
            "salary_from": 100000,
        }
        return result


class TestJobMatcherClassifierIntegration:
    """Интеграционные тесты job_matcher + classifier."""

    @pytest.mark.asyncio
    async def test_full_pipeline_save_classify_update(
        self,
        db_session: AsyncSession,
        setup_categories,
    ):
        """
        Полный пайплайн: сохранение → классификация → обновление.

        1. JobOffer сохраняется
        2. Классифицируется
        3. Обновляется category_ids
        """
        bus = InMemoryProducer()
        job_matcher_service = JobMatcherService(
            offer_repo=JobOfferRepository(model=JobOffer),
            sub_repo=None,
            bus=bus,
        )
        classifier_service = ClassifierService(
            repository=CategoryRepository(),
            log_repository=ClassificationLogRepository(),
            message_bus=bus,
            category_classifier=MockCategoryClassifier(),
            entity_extractor=MockEntityExtractor(),
        )

        # 1. Сохраняем JobOffer
        text = "Python разработчик, Django, REST API"
        job_offer = await job_matcher_service.save_job_offer(
            session=db_session,
            text=text,
            chat_id=123456,
        )
        assert job_offer.id is not None
        assert job_offer.category_ids is None

        # 2. Классифицируем
        result = await classifier_service.process_classify_request(
            session=db_session,
            request_id=job_offer.id,
            text=text,
        )
        assert result is not None
        assert "category_ids" in result
        assert len(result["category_ids"]) == 2

        # 3. Обновляем JobOffer
        await job_matcher_service.update_job_offer_categories(
            session=db_session,
            job_offer_id=job_offer.id,
            category_ids=result["category_ids"],
        )

        # 4. Проверяем что обновился
        await db_session.refresh(job_offer)
        assert job_offer.category_ids is not None
        assert len(job_offer.category_ids) == 2

    @pytest.mark.asyncio
    async def test_classifier_logs_request(
        self,
        db_session: AsyncSession,
        setup_categories,
    ):
        """
        Классификатор записывает лог в БД.
        """
        bus = InMemoryProducer()
        classifier_service = ClassifierService(
            repository=CategoryRepository(),
            log_repository=ClassificationLogRepository(),
            message_bus=bus,
            category_classifier=MockCategoryClassifier(),
            entity_extractor=MockEntityExtractor(),
        )

        request_id = uuid.uuid4()
        text = "Test vacancy"

        await classifier_service.process_classify_request(
            session=db_session,
            request_id=request_id,
            text=text,
        )

        # Проверяем лог
        from src.modules.classifier.models import ClassificationLog

        stmt = select(ClassificationLog).where(ClassificationLog.request_id == request_id)
        result = await db_session.execute(stmt)
        log = result.scalars().first()
        assert log is not None
        assert log.text_hash is not None
        assert "Test" in log.text_preview
        assert log.category_slug in ["backend", "frontend"]
        assert log.confidence > 0

    @pytest.mark.asyncio
    async def test_job_offer_with_multiple_categories(
        self,
        db_session: AsyncSession,
        setup_categories,
    ):
        """
        JobOffer получает несколько категорий.
        """
        bus = InMemoryProducer()
        job_matcher_service = JobMatcherService(
            offer_repo=JobOfferRepository(model=JobOffer),
            sub_repo=None,
            bus=bus,
        )
        classifier_service = ClassifierService(
            repository=CategoryRepository(),
            log_repository=ClassificationLogRepository(),
            message_bus=bus,
            category_classifier=MockCategoryClassifier(),
            entity_extractor=MockEntityExtractor(),
        )

        # Сохраняем
        job_offer = await job_matcher_service.save_job_offer(
            session=db_session,
            text="Fullstack developer",
            chat_id=111,
        )

        # Классифицируем
        result = await classifier_service.process_classify_request(
            session=db_session,
            request_id=job_offer.id,
            text="Fullstack developer Python + React",
        )

        # Должно быть 2 категории
        assert len(result["category_ids"]) == 2
        assert len(result["categories"]) == 2

        # Обновляем
        await job_matcher_service.update_job_offer_categories(
            session=db_session,
            job_offer_id=job_offer.id,
            category_ids=result["category_ids"],
        )

        # Проверяем
        await db_session.refresh(job_offer)
        assert len(job_offer.category_ids) == 2

    @pytest.mark.asyncio
    async def test_bus_event_published_on_classification(
        self,
        db_session: AsyncSession,
        setup_categories,
    ):
        """
        Classifier публикует событие TEXT_CLASSIFY_COMPLETED.
        """
        bus = MockBus()
        classifier_service = ClassifierService(
            repository=CategoryRepository(),
            log_repository=ClassificationLogRepository(),
            message_bus=bus,
            category_classifier=MockCategoryClassifier(),
            entity_extractor=MockEntityExtractor(),
        )

        await classifier_service.process_classify_request(
            session=db_session,
            request_id=uuid.uuid4(),
            text="Test text",
        )

        # Проверяем что событие опубликовано
        assert len(bus.published) > 0
        topics = [topic for topic, _ in bus.published]
        assert BusTopics.TEXT_CLASSIFY_COMPLETED in topics


@pytest.fixture
async def setup_categories(db_session: AsyncSession):
    """Создаёт тестовые категории."""
    repo = CategoryRepository()
    categories = []
    for slug, name in [
        ("backend", "Backend-разработка"),
        ("frontend", "Frontend-разработка"),
        ("data_science", "Data Science"),
    ]:
        cat = await repo.create(
            db_session,
            {
                "name": name,
                "slug": slug,
                "description": f"Категория {name}",
                "is_active": True,
            },
        )
        categories.append(cat)
    await db_session.commit()
    return categories
