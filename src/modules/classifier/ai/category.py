"""Zero-shot классификатор категорий на основе GLiClass."""

import asyncio
import logging
import uuid
from dataclasses import dataclass
from typing import Any

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
    Multi-label zero-shot классификатор на основе GLiClass.

    Модель инициализируется явно через initialize() при старте приложения.
    """

    def __init__(
        self,
        model_name: str = "knowledgator/gliclass-large-v1.0",
        device: int = -1,
        threshold: float = 0.5,
    ) -> None:
        """
        Args:
            model_name: Название модели HuggingFace.
            device: Устройство (-1 = CPU, 0 = GPU).
            threshold: Минимальная уверенность для включения категории.
        """
        self._model_name = model_name
        self._device = device
        self._threshold = threshold
        self._pipeline: Any | None = None
        self._initialized = False

    @property
    def _pipeline_device(self) -> str:
        """Преобразовать числовую настройку устройства в формат GLiClass."""
        return "cpu" if self._device < 0 else f"cuda:{self._device}"

    async def initialize(self) -> None:
        """Инициализация pipeline. Вызывается при старте приложения."""
        try:

            logger.info("Загрузка модели %s (device=%s)...", self._model_name, self._device)

            loop = asyncio.get_running_loop()

            def _load() -> None:
                from gliclass import GLiClassModel, ZeroShotClassificationPipeline
                from transformers import AutoTokenizer

                model = GLiClassModel.from_pretrained(self._model_name)
                tokenizer = AutoTokenizer.from_pretrained(self._model_name)
                self._pipeline = ZeroShotClassificationPipeline(
                    model,
                    tokenizer,
                    classification_type="multi-label",
                    device=self._pipeline_device,
                )

            await loop.run_in_executor(None, _load)
            self._initialized = True
            logger.info("Модель %s загружена", self._model_name)
        except ImportError:
            logger.error("gliclass или transformers не установлен. Классификация недоступна.")
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
        if not labels:
            return ClassifyResult(categories=[])

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
                lambda: self._pipeline(
                    text,
                    label_names,
                    threshold=self._threshold,
                )[0],
            )

            # GLiClass result: [{"label": str, "score": float}, ...]
            name_to_label = {label["name"]: label for label in labels}

            categories = []
            for prediction in sorted(
                result,
                key=lambda item: item["score"],
                reverse=True,
            ):
                label_name = prediction["label"]
                label_info = name_to_label.get(label_name)
                if label_info:
                    logger.info("Category: %s %s", label_info["name"], prediction["score"])
                    categories.append(
                        CategoryScore(
                            id=label_info["id"],
                            slug=label_info["slug"],
                            name=label_info["name"],
                            confidence=float(prediction["score"]),
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
            threshold=settings.CLASSIFIER_THRESHOLD,
        )
    return _classifier_instance
