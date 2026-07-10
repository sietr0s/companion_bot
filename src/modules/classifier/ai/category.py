"""Zero-shot классификатор категорий на основе BART."""

import logging
import uuid
from dataclasses import dataclass

from src.modules.classifier.ai.base import CategoryClassifier, CategoryScore, ClassifyResult

logger = logging.getLogger(__name__)


@dataclass
class _LabelInfo:
    """Внутреннее представление лейбла."""

    id: uuid.UUID
    slug: str
    name: str


class ZeroShotCategoryClassifier:
    """
    Zero-shot классификатор на основе facebook/bart-large-mnli.

    Использует transformers.pipeline для классификации текста
    без дополнительного обучения.
    """

    def __init__(self) -> None:
        self._pipeline = None
        self._initialized = False

    def _get_pipeline(self):
        """Ленивая инициализация pipeline."""
        if self._pipeline is None:
            try:
                from transformers import pipeline

                logger.info("Загрузка модели facebook/bart-large-mnli...")
                self._pipeline = pipeline(
                    "zero-shot-classification",
                    model="facebook/bart-large-mnli",
                    device=-1,  # CPU
                )
                logger.info("Модель загружена")
            except ImportError:
                logger.error("transformers не установлен. Заглушка вместо классификации.")
                self._initialized = False
            except Exception as e:
                logger.exception("Ошибка загрузки модели: %s", e)
                self._initialized = False
        return self._pipeline

    async def classify(self, text: str, labels: list[dict]) -> ClassifyResult:
        """
        Классифицировать текст по категориям.

        Args:
            text: Текст для классификации.
            labels: [{"id": UUID, "slug": str, "name": str}, ...].

        Returns:
            ClassifyResult со всеми категориями по убыванию confidence.
        """
        pipeline = self._get_pipeline()

        # Если модель не загрузилась — возвращаем пустой результат
        if pipeline is None:
            logger.warning("Модель не загружена, возвращаем пустой результат")
            return ClassifyResult(categories=[])

        # Извлекаем имена лейблов для модели
        label_names = [label["name"] for label in labels]

        try:
            # Запускаем классификацию
            result = pipeline(text, label_names, multi_label=False)

            # Маппинг результата обратно в CategoryScore
            # result: {"labels": [...], "scores": [...], "sequence": "..."}
            name_to_label = {label["name"]: label for label in labels}

            categories = []
            for label_name, score in zip(result["labels"], result["scores"]):
                label_info = name_to_label.get(label_name)
                if label_info:
                    categories.append(
                        CategoryScore(
                            id=label_info["id"],
                            slug=label_info["slug"],
                            name=label_info["name"],
                            confidence=float(score),
                        )
                    )

            return ClassifyResult(categories=categories)

        except Exception as e:
            logger.exception("Ошибка классификации: %s", e)
            return ClassifyResult(categories=[])


# Singleton для ленивой инициализации
_classifier_instance: ZeroShotCategoryClassifier | None = None


def get_category_classifier() -> CategoryClassifier:
    """Получить singleton экземпляр классификатора."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = ZeroShotCategoryClassifier()
    return _classifier_instance
