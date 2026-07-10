"""Regex-based извлечение сущностей из текста вакансий."""

import logging
import re

from src.modules.classifier.ai.base import EntityExtractor, EntityResult

logger = logging.getLogger(__name__)


class RegexEntityExtractor:
    """
    Извлечение сущностей с помощью regex-паттернов.

    Поддерживаемые сущности:
    - salary_min, salary_max: зарплатные ожидания
    - type: тип занятости (remote, office, project)
    - stack: технологии (заглушка)
    """

    # Паттерны для зарплат
    SALARY_PATTERNS = [
        # "30000-50000 руб", "30к-50к" (диапазон - первый приоритет)
        r"(\d+)\s*[-–]\s*(\d+)\s*(?:к|тыс|тысяч|руб|рублей|rur|₽)?",
        # "от 150к до 250к" (диапазон от...до)
        r"от\s*(\d+)\s*(?:к|тыс|тысяч|руб|рублей|rur|₽)?\s*до\s*(\d+)",
        # "от 30000 руб", "от 30к", "от 30 тыс"
        r"от\s*(\d+)\s*(?:к|тыс|тысяч|руб|рублей|rur|₽)?",
        # "до 50000 руб", "до 50к"
        r"до\s*(\d+)\s*(?:к|тыс|тысяч|руб|рублей|rur|₽)?",
        # "бюджет до 100к"
        r"бюджет\s*(?:до)?\s*(\d+)\s*(?:к|тыс|тысяч|руб|рублей|rur|₽)?",
        # "зп 40000"
        r"зп\s*(?:от)?\s*(\d+)\s*(?:к|тыс|тысяч|руб|рублей|rur|₽)?",
    ]

    # Паттерны для типа занятости
    TYPE_PATTERNS = {
        "remote": [r"\b(удалённо|remote|удаленная|удалённая|удалёнка|удаленка)\b"],
        "office": [r"\b(офис|office|офисный|офисе)\b"],
        "project": [r"\b(проект|project|проектная|проектную)\b"],
    }

    # Паттерны для стека (заглушка)
    STACK_PATTERNS = [
        r"\b(figma)\b",
        r"\b(photoshop)\b",
        r"\b(python)\b",
        r"\b(react)\b",
        r"\b(vue)\b",
        r"\b(angular)\b",
        r"\b(node\.?js)\b",
        r"\b(django)\b",
        r"\b(fastapi)\b",
        r"\b(flask)\b",
        r"\b(java)\b",
        r"\b(golang|go)\b",
    ]

    async def extract(self, text: str) -> EntityResult:
        """
        Извлечь сущности из текста.

        Args:
            text: Текст вакансии.

        Returns:
            EntityResult с извлечёнными сущностями.
        """
        text_lower = text.lower()

        entities = {}

        # Извлекаем зарплату
        salary = self._extract_salary(text_lower)
        if salary:
            entities.update(salary)

        # Извлекаем тип занятости
        emp_type = self._extract_type(text_lower)
        if emp_type:
            entities["type"] = emp_type

        # Извлекаем стек
        stack = self._extract_stack(text_lower)
        if stack:
            entities["stack"] = stack

        return EntityResult(entities=entities)

    def _extract_salary(self, text: str) -> dict | None:
        """Извлечь зарплатные ожидания."""
        for pattern in self.SALARY_PATTERNS:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    # Диапазон "30-50" или "от 150 до 250"
                    return {
                        "salary_min": int(groups[0]) * 1000,
                        "salary_max": int(groups[1]) * 1000,
                    }
                elif len(groups) == 1:
                    # Одно значение "от 30" или "до 50"
                    value = int(groups[0])
                    # Если число больше 1000, скорее всего это уже рубли, а не тысячи
                    if value < 1000:
                        value *= 1000
                    # Проверяем контекст вокруг всего матча
                    full_match = match.group(0)
                    if "от" in full_match:
                        return {"salary_min": value}
                    elif "до" in full_match or "бюджет" in full_match:
                        return {"salary_max": value}
                    else:
                        return {"salary_min": value}
        return None

    def _extract_type(self, text: str) -> str | None:
        """Извлечь тип занятости."""
        for emp_type, patterns in self.TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    return emp_type
        return None

    def _extract_stack(self, text: str) -> list[str]:
        """Извлечь технологии из текста."""
        stack = []
        for pattern in self.STACK_PATTERNS:
            match = re.search(pattern, text)
            if match:
                stack.append(match.group(1))
        return stack


# Singleton
_extractor_instance: RegexEntityExtractor | None = None


def get_entity_extractor() -> EntityExtractor:
    """Получить singleton экземпляр экстрактора."""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = RegexEntityExtractor()
    return _extractor_instance
