"""DI-зависимости модуля classifier."""

from fastapi import Depends

from src.bus.interface import MessageBus
from src.bus import get_producer
from src.modules.classifier.ai.category import get_category_classifier
from src.modules.classifier.ai.ner import get_entity_extractor
from src.modules.classifier.repository import (
    CategoryRepository,
    ClassificationLogRepository,
)
from src.modules.classifier.service import ClassifierService


def get_category_repository() -> CategoryRepository:
    """Фабрика репозитория категорий."""
    return CategoryRepository()


def get_classification_log_repository() -> ClassificationLogRepository:
    """Фабрика репозитория логов классификации."""
    return ClassificationLogRepository()


def get_classifier_service(
    repository: CategoryRepository = Depends(get_category_repository),
    log_repository: ClassificationLogRepository = Depends(get_classification_log_repository),
    message_bus: MessageBus = Depends(get_producer),
    category_classifier=Depends(get_category_classifier),
    entity_extractor=Depends(get_entity_extractor),
) -> ClassifierService:
    """Фабрика сервиса классификации."""
    return ClassifierService(
        repository=repository,
        log_repository=log_repository,
        message_bus=message_bus,
        category_classifier=category_classifier,
        entity_extractor=entity_extractor,
    )


def get_classifier_service_factory(
    bus: MessageBus | None = None,
):
    """
    Фабрика (session, service) для обработчиков шины.

    Возвращает кортеж (session, ClassifierService) для использования
    в обработчиках событий шины.

    Args:
        bus: Шина сообщений. Если None, используется шина по умолчанию.
    """
    return ClassifierService(
        repository=CategoryRepository(),
        log_repository=ClassificationLogRepository(),
        message_bus=bus,
        category_classifier=get_category_classifier(),
        entity_extractor=get_entity_extractor(),
    )
