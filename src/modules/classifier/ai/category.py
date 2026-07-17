"""Zero-shot классификатор категорий на основе BART."""

import asyncio
import logging
import uuid
from dataclasses import dataclass

from transformers import pipeline

from src.core.config import settings
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
    Zero-shot классификатор на основе transformers pipeline.

    Использует transformers.pipeline для классификации текста
    без дополнительного обучения. Модель инициализируется явно
    через метод initialize() при старте приложения.
    """

    def __init__(self, model_name: str = "facebook/bart-large-mnli", device: int = -1) -> None:
        """
        Args:
            model_name: Название модели HuggingFace.
            device: Устройство (-1 = CPU, 0 = GPU).
        """
        self._model_name = model_name
        self._device = device
        self._pipeline = None
        self._initialized = False

    async def initialize(self) -> None:
        """Инициализация pipeline. Вызывается при старте приложения."""
        try:

            logger.info("Загрузка модели %s (device=%s)...", self._model_name, self._device)

            loop = asyncio.get_running_loop()

            def _load() -> None:
                self._pipeline = pipeline(
                    "zero-shot-classification",
                    model=self._model_name,
                    device=self._device,
                )

            await loop.run_in_executor(None, _load)
            self._initialized = True
            logger.info("Модель %s загружена", self._model_name)
        except ImportError:
            logger.error("transformers не установлен. Классификация недоступна.")
            self._initialized = False
        except Exception as e:
            logger.exception("Ошибка загрузки модели %s: %s", self._model_name, e)
            self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Флаг: модель загружена."""
        return self._initialized

    async def classify(self, text: str, labels: list[dict]) -> ClassifyResult:
        """
        Классифицировать текст по категориям.

        Args:
            text: Текст для классификации.
            labels: [{"id": UUID, "slug": str, "name": str}, ...].

        Returns:
            ClassifyResult со всеми категориями по убыванию confidence.
        """
        # Если модель не загрузилась — возвращаем пустой результат
        if self._pipeline is None:
            logger.warning("Модель не загружена, возвращаем пустой результат")
            return ClassifyResult(categories=[])

        # Извлекаем имена лейблов для модели
        label_names = [label["name"] for label in labels]

        try:
            # Запускаем классификацию в executor, чтобы не блокировать event loop
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._pipeline(text, label_names, multi_label=False),
            )

            # Маппинг результата обратно в CategoryScore
            # result: {"labels": [...], "scores": [...], "sequence": "..."}
            name_to_label = {label["name"]: label for label in labels}

            categories = []
            for label_name, score in zip(result["labels"], result["scores"], strict=True):
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


# Singleton для явной инициализации
_classifier_instance: ZeroShotCategoryClassifier | None = None


def get_category_classifier() -> CategoryClassifier:
    """Получить singleton экземпляр классификатора."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = ZeroShotCategoryClassifier(
            model_name=settings.CLASSIFIER_MODEL_NAME,
            device=settings.CLASSIFIER_DEVICE,
        )
    return _classifier_instance
