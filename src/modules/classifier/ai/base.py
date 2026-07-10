"""AI-интерфейсы модуля classifier."""

import uuid
from dataclasses import dataclass
from typing import Protocol


@dataclass
class CategoryScore:
    """Результат классификации по категории."""

    id: uuid.UUID
    slug: str
    name: str
    confidence: float


@dataclass
class ClassifyResult:
    """Результат классификации текста."""

    categories: list[CategoryScore]


@dataclass
class EntityResult:
    """Результат извлечения сущностей."""

    entities: dict


class CategoryClassifier(Protocol):
    """Протокол классификатора категорий."""

    async def classify(self, text: str, labels: list[dict]) -> ClassifyResult:
        """
        Классифицировать текст по категориям.

        Args:
            text: Текст для классификации.
            labels: Список категорий [{"id": UUID, "slug": str, "name": str}, ...].

        Returns:
            ClassifyResult со всеми категориями, отсортированными по confidence.
        """
        ...


class EntityExtractor(Protocol):
    """Протокол извлечения сущностей."""

    async def extract(self, text: str) -> EntityResult:
        """
        Извлечь сущности из текста.

        Args:
            text: Текст для извлечения сущностей.

        Returns:
            EntityResult с извлечёнными сущностями.
        """
        ...
