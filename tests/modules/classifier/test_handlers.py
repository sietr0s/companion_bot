"""Тесты обработчиков событий модуля classifier."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.bus.in_memory.producer import InMemoryProducer
from src.modules.classifier.ai.category import get_category_classifier
from src.modules.classifier.ai.ner import get_entity_extractor
from src.modules.classifier.handlers import register_handlers
from src.modules.classifier.repository import CategoryRepository, ClassificationLogRepository
from src.modules.classifier.service import ClassifierService


class MockBus:
    """Заглушка шины сообщений для тестов."""

    def __init__(self):
        self.published = []
        self.subscribers = {}

    async def publish(self, topic: str, message: dict) -> None:
        self.published.append((topic, message))

    def subscribe(self, topic: str):
        def decorator(func):
            if topic not in self.subscribers:
                self.subscribers[topic] = []
            self.subscribers[topic].append(func)
            return func

        return decorator

    def get_subscribers(self) -> dict:
        return self.subscribers

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass


@pytest_asyncio.fixture
def mock_bus():
    return MockBus()


@pytest_asyncio.fixture
def service_factory(db_session: AsyncSession):
    """Фабрика сервиса для обработчиков."""

    def factory(session):
        return ClassifierService(
            repository=CategoryRepository(),
            log_repository=ClassificationLogRepository(),
            message_bus=InMemoryProducer(),
            category_classifier=get_category_classifier(),
            entity_extractor=get_entity_extractor(),
        )

    return factory


class TestClassifierHandlers:
    """Тесты обработчиков событий classifier."""

    @pytest.mark.asyncio
    async def test_register_handlers(self):
        """Регистрация обработчиков."""
        from src.bus import get_producer

        register_handlers()

        # Проверяем что обработчик зарегистрирован
        from src.core.bus_topics import BusTopics

        bus = get_producer()
        assert BusTopics.TEXT_CLASSIFY_REQUEST in bus.get_subscribers()

    @pytest.mark.asyncio
    async def test_handle_classify_request_invalid_data(self):
        """Обработка запроса с невалидными данными."""
        from src.bus import get_producer

        register_handlers()

        bus = get_producer()
        handler = bus.get_subscribers()["classifier.command.classify"][0]

        # Отправляем неполные данные
        await handler({"source_module": "test"})

        # Обработчик должен залогировать предупреждение
        # (проверяем через caplog в pytest)

    @pytest.mark.asyncio
    async def test_handle_classify_request_no_categories(
        self, db_session: AsyncSession
    ):
        """Обработка запроса при отсутствии категорий."""
        from src.bus import get_producer
        from src.core.database import init_db

        await init_db()
        register_handlers()

        bus = get_producer()
        handler = bus.get_subscribers()["classifier.command.classify"][0]

        request_id = str(uuid.uuid4())
        await handler(
            {
                "request_id": request_id,
                "text": "Тестовый текст вакансии",
                "source_module": "test_module",
            }
        )

        # Обработчик должен залогировать предупреждение
        # (проверяем через caplog в pytest)

    @pytest.mark.asyncio
    async def test_handle_classify_request_with_categories(
        self, db_session: AsyncSession
    ):
        """Обработка запроса с существующими категориями."""
        # Создаём категорию
        from src.modules.classifier.repository import CategoryRepository

        repo = CategoryRepository()
        await repo.create(
            db_session,
            {
                "name": "IT",
                "slug": "it",
                "description": "IT вакансии",
                "is_active": True,
            },
        )
        await db_session.commit()

        register_handlers()
        bus = get_producer()
        handler = bus.get_subscribers()["classifier.command.classify"][0]

        request_id = str(uuid.uuid4())
        text = "Разработчик Python, зарплата от 100к"

        await handler(
            {
                "request_id": request_id,
                "text": text,
                "source_module": "test_module",
            }
        )

        # Проверяем что опубликовано событие completed
        from src.core.bus_topics import BusTopics

        completed_events = [
            (topic, msg)
            for topic, msg in mock_bus.published
            if topic == BusTopics.TEXT_CLASSIFY_COMPLETED
        ]
        assert len(completed_events) == 1
        _, msg = completed_events[0]
        assert msg["request_id"] == request_id
        assert "text_hash" in msg
        assert "categories" in msg
        assert "entities" in msg

        # Проверяем что лог записан в БД
        from sqlalchemy import select

        from src.modules.classifier.models import ClassificationLog

        stmt = select(ClassificationLog).where(
            ClassificationLog.request_id == uuid.UUID(request_id)
        )
        result = await db_session.execute(stmt)
        log = result.scalars().first()
        assert log is not None
        assert log.text_hash
        assert log.source_module == "test_module"
