"""Тесты сервисов модуля classifier."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.bus.in_memory.producer import InMemoryProducer
from src.core.exceptions import ConflictError, NotFoundError
from src.modules.classifier.ai.category import get_category_classifier
from src.modules.classifier.ai.ner import get_entity_extractor
from src.modules.classifier.repository import (
    CategoryRepository,
    ClassificationLogRepository,
)
from src.modules.classifier.schemas.public.category import CategoryCreate, CategoryUpdate
from src.modules.classifier.service import ClassifierService


@pytest_asyncio.fixture
def classifier_service():
    """Фабрика сервиса классификации для тестов."""
    return ClassifierService(
        repository=CategoryRepository(),
        log_repository=ClassificationLogRepository(),
        message_bus=InMemoryProducer(),
        category_classifier=get_category_classifier(),
        entity_extractor=get_entity_extractor(),
    )


class TestClassifierServiceCreateCategory:
    """Тесты создания категорий."""

    @pytest.mark.asyncio
    async def test_create_category_success(self, db_session: AsyncSession, classifier_service):
        """Успешное создание категории."""
        data = CategoryCreate(
            name="IT Вакансии",
            slug="it_vacancies",
            description="Категория для IT вакансий",
            is_active=True,
        )
        category = await classifier_service.create_category(db_session, data)

        assert category.name == "IT Вакансии"
        assert category.slug == "it_vacancies"
        assert category.description == "Категория для IT вакансий"
        assert category.is_active is True
        assert category.id

    @pytest.mark.asyncio
    async def test_create_category_duplicate_slug(
        self, db_session: AsyncSession, classifier_service
    ):
        """Ошибка при дублировании slug."""
        data = CategoryCreate(
            name="IT Вакансии",
            slug="it_vacancies",
            description="Категория для IT вакансий",
        )
        await classifier_service.create_category(db_session, data)

        duplicate_data = CategoryCreate(
            name="Другие IT Вакансии",
            slug="it_vacancies",  # Тот же slug
            description="Другое описание",
        )

        with pytest.raises(ConflictError) as exc_info:
            await classifier_service.create_category(db_session, duplicate_data)
        assert "slug" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_create_category_duplicate_name(
        self, db_session: AsyncSession, classifier_service
    ):
        """Ошибка при дублировании name."""
        data = CategoryCreate(
            name="Уникальное Имя",
            slug="unique_name",
            description="Описание",
        )
        await classifier_service.create_category(db_session, data)

        duplicate_data = CategoryCreate(
            name="Уникальное Имя",  # То же имя
            slug="another_slug",
            description="Другое описание",
        )

        with pytest.raises(ConflictError) as exc_info:
            await classifier_service.create_category(db_session, duplicate_data)
        assert "name" in str(exc_info.value.detail).lower()


class TestClassifierServiceUpdateCategory:
    """Тесты обновления категорий."""

    @pytest.mark.asyncio
    async def test_update_category_success(self, db_session: AsyncSession, classifier_service):
        """Успешное обновление категории."""
        create_data = CategoryCreate(
            name="Old Name",
            slug="old_slug",
            description="Old description",
        )
        await classifier_service.create_category(db_session, create_data)

        update_data = CategoryUpdate(
            name="New Name",
            description="New description",
        )
        updated = await classifier_service.update_category(db_session, "old_slug", update_data)

        assert updated.name == "New Name"
        assert updated.description == "New description"
        assert updated.slug == "old_slug"  # slug не менялся

    @pytest.mark.asyncio
    async def test_update_category_not_found(self, db_session: AsyncSession, classifier_service):
        """Ошибка при обновлении несуществующей категории."""
        update_data = CategoryUpdate(name="New Name")

        with pytest.raises(NotFoundError) as exc_info:
            await classifier_service.update_category(db_session, "nonexistent_slug", update_data)
        assert "не найдена" in str(exc_info.value.detail).lower()


class TestClassifierServiceDeleteCategory:
    """Тесты удаления категорий."""

    @pytest.mark.asyncio
    async def test_delete_category_success(self, db_session: AsyncSession, classifier_service):
        """Успешное удаление категории."""
        create_data = CategoryCreate(
            name="ToDelete",
            slug="to_delete",
            description="Будет удалена",
        )
        await classifier_service.create_category(db_session, create_data)

        await classifier_service.delete_category(db_session, "to_delete")

        # Проверка что удалена
        with pytest.raises(NotFoundError):
            await classifier_service.update_category(
                db_session, "to_delete", CategoryUpdate(name="x")
            )

    @pytest.mark.asyncio
    async def test_delete_category_not_found(self, db_session: AsyncSession, classifier_service):
        """Ошибка при удалении несуществующей категории."""
        with pytest.raises(NotFoundError) as exc_info:
            await classifier_service.delete_category(db_session, "nonexistent_slug")
        assert "не найдена" in str(exc_info.value.detail).lower()


class TestClassifierServiceGetAllCategories:
    """Тесты получения списка категорий."""

    @pytest.mark.asyncio
    async def test_get_all_categories_empty(self, db_session: AsyncSession, classifier_service):
        """Получение пустого списка."""
        categories, total = await classifier_service.get_all_categories(db_session)
        assert categories == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_get_all_categories_with_data(self, db_session: AsyncSession, classifier_service):
        """Получение списка с данными."""
        for i in range(3):
            data = CategoryCreate(
                name=f"Category {i}",
                slug=f"category_{i}",
                description=f"Description {i}",
            )
            await classifier_service.create_category(db_session, data)

        categories, total = await classifier_service.get_all_categories(db_session)
        assert total == 3
        assert len(categories) == 3
        assert all(cat.name.startswith("Category") for cat in categories)


class TestClassifierServiceProcessClassifyRequest:
    """Тесты обработки запросов на классификацию."""

    @pytest.mark.asyncio
    async def test_classify_empty_categories(self, db_session: AsyncSession, classifier_service):
        """Классификация при отсутствии категорий."""
        request_id = uuid.uuid4()
        text = "Разработчик Python, зарплата от 100к"

        # Не создаём категории — должен вернуть пустой результат
        await classifier_service.process_classify_request(
            session=db_session,
            request_id=request_id,
            text=text,
        )

        # Проверяем что лог не создан (нет категорий)
        logs, _ = await classifier_service.log_repository.get_list(db_session)
        assert len(logs) == 0

    @pytest.mark.asyncio
    async def test_classify_with_categories(self, db_session: AsyncSession, classifier_service):
        """Классификация с существующими категориями."""
        # Создаём категорию
        create_data = CategoryCreate(
            name="IT",
            slug="it",
            description="IT вакансии",
        )
        await classifier_service.create_category(db_session, create_data)

        request_id = uuid.uuid4()
        text = "Разработчик Python, зарплата от 100к"

        await classifier_service.process_classify_request(
            session=db_session,
            request_id=request_id,
            text=text,
        )

        # Проверяем что лог создан
        logs, total = await classifier_service.log_repository.get_list(db_session)
        assert total >= 1

        # Находим наш лог по request_id
        our_log = None
        for log in logs:
            if log.request_id == request_id:
                our_log = log
                break

        assert our_log is not None
        assert our_log.text_hash
        assert our_log.text_preview == text[:200]
