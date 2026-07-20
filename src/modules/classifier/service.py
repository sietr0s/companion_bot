"""Сервис модуля classifier."""

import hashlib
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.service import BaseService
from src.bus.interface import MessageProducer
from src.core.bus_topics import BusTopics
from src.core.exceptions import ConflictError, NotFoundError
from src.modules.classifier.ai.base import CategoryClassifier, EntityExtractor
from src.modules.classifier.default_categories import DEFAULT_CATEGORIES
from src.modules.classifier.models import Category
from src.modules.classifier.repository import (
    CategoryRepository,
    ClassificationLogRepository,
)
from src.modules.classifier.schemas.events import (
    CategoryScore,
    TextClassifyCompleted,
)
from src.modules.classifier.schemas.public.category import CategoryCreate, CategoryUpdate


class ClassifierService(BaseService[CategoryRepository, Category]):
    """
    Сервис классификации текстов.

    Управляет категориями и обрабатывает запросы на классификацию.
    """

    def __init__(
        self,
        repository: CategoryRepository,
        log_repository: ClassificationLogRepository,
        message_bus: MessageProducer,
        category_classifier: CategoryClassifier,
        entity_extractor: EntityExtractor,
    ) -> None:
        super().__init__(repository)
        self.log_repository = log_repository
        self.message_bus = message_bus
        self.category_classifier = category_classifier
        self.entity_extractor = entity_extractor

    # --- CRUD категорий ---

    async def create_category(self, session: AsyncSession, data: CategoryCreate) -> Category:
        """
        Создать категорию.

        Проверяет уникальность slug.
        """
        # Проверка уникальности slug
        existing = await self.repository.get_by_slug(session, data.slug)
        if existing:
            raise ConflictError(detail="Категория с таким slug уже существует")

        # Проверка уникальности name
        existing = await self.repository.get_by_name(session, data.name)
        if existing:
            raise ConflictError(detail="Категория с таким name уже существует")

        return await self.repository.create(session, data.model_dump())

    async def update_category(
        self, session: AsyncSession, slug: str, data: CategoryUpdate
    ) -> Category:
        """
        Обновить категорию.

        Находит по slug, обновляет только указанные поля.
        """
        category = await self.repository.get_by_slug(session, slug)
        if not category:
            raise NotFoundError(detail="Категория не найдена")

        # Если меняем slug — проверяем уникальность
        if data.name is not None and data.name != category.name:
            existing = await self.repository.get_by_name(session, data.name)
            if existing and existing.id != category.id:
                raise ConflictError(detail="Категория с таким name уже существует")

        update_data = data.model_dump(exclude_unset=True)
        return await self.repository.update(session, category, update_data)

    async def delete_category(self, session: AsyncSession, slug: str) -> None:
        """Удалить категорию по slug."""
        category = await self.repository.get_by_slug(session, slug)
        if not category:
            raise NotFoundError(detail="Категория не найдена")
        await self.repository.delete(session, category)

    async def get_all_categories(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        order_by: str | None = "-created_at",
    ) -> tuple[list[Category], int]:
        """Получить список всех категорий с пагинацией."""
        return await self.repository.get_list(
            session,
            skip=skip,
            limit=limit,
            order_by=order_by,
        )

    async def init_default_categories(self, session: AsyncSession) -> None:
        """
        Создать категории по умолчанию, если их нет.

        Вызывается при старте приложения один раз.
        Управляет транзакцией самостоятельно.
        """
        # Проверяем есть ли уже категории
        existing, _ = await self.get_all_categories(session, limit=1)
        if existing:
            return  # Категории уже есть

        # Создаём категории по умолчанию
        for default_cat in DEFAULT_CATEGORIES:
            try:
                data = CategoryCreate(
                    name=default_cat.name,
                    slug=default_cat.slug,
                    description=default_cat.description,
                    is_active=True,
                )
                await self.create_category(session, data)
            except ConflictError:
                # Категория уже существует — пропускаем
                continue

    # --- Классификация ---

    async def process_classify_request(
        self,
        session: AsyncSession,
        request_id: uuid.UUID,
        text: str,
    ) -> dict | None:
        """
        Обработать запрос на классификацию текста.

        1. Получить активные лейблы из БД
        2. Если лейблов нет — опубликовать TextClassifyCompleted с categories=[]
        3. Вызвать category_classifier.classify(text, labels)
        4. Вызвать entity_extractor.extract(text)
        5. Записать ClassificationLog
        6. Опубликовать TextClassifyCompleted

        Returns:
            dict с category_ids и categories для обновления JobOffer,
            или None если категорий нет.
        """
        # 1. Получаем активные лейблы
        labels = await self.repository.get_active_labels(session)

        # 2. Если лейблов нет — возвращаем пустой результат
        if not labels:
            event = TextClassifyCompleted(
                request_id=request_id,
                text_hash=hashlib.sha256(text.encode()).hexdigest(),
                categories=[],
                entities={},
            )
            await self.message_bus.publish(BusTopics.TEXT_CLASSIFY_COMPLETED, event.to_bus_dict())
            return None

        # 3. Классифицируем текст
        classify_result = await self.category_classifier.classify(text, labels)

        # 4. Извлекаем сущности
        entity_result = await self.entity_extractor.extract(text)

        # 5. Записываем лог
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        text_preview = text[:200]

        # Топ-1 категория для логирования
        top_category = classify_result.categories[0] if classify_result.categories else None
        category_slug = top_category.slug if top_category else "unknown"
        confidence = top_category.confidence if top_category else 0.0

        # Все категории для JobOffer
        category_ids = [cat.id for cat in classify_result.categories]

        # Все scores для логирования
        all_scores = {cat.slug: cat.confidence for cat in classify_result.categories}

        # Добавляем _all_scores в entities
        entities = entity_result.entities.copy()
        entities["_all_scores"] = all_scores

        # Записываем лог через репозиторий
        await self.log_repository.create(
            session,
            {
                "text_hash": text_hash,
                "text_preview": text_preview,
                "category_slug": category_slug,
                "confidence": confidence,
                "entities": entities,
                "request_id": request_id,
            },
        )

        # 6. Публикуем результат
        event = TextClassifyCompleted(
            request_id=request_id,
            text_hash=text_hash,
            categories=[
                CategoryScore(
                    id=cat.id,
                    slug=cat.slug,
                    name=cat.name,
                    confidence=cat.confidence,
                )
                for cat in classify_result.categories
            ],
            entities=entity_result.entities,
        )
        await self.message_bus.publish(BusTopics.TEXT_CLASSIFY_COMPLETED, event.to_bus_dict())

        # Возвращаем результат для обновления JobOffer
        return {
            "category_ids": [str(cat_id) for cat_id in category_ids],
            "categories": [
                {
                    "id": str(cat.id),
                    "slug": cat.slug,
                    "name": cat.name,
                    "confidence": cat.confidence,
                }
                for cat in classify_result.categories
            ],
        }
