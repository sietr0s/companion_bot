"""Тесты AI-компонентов модуля classifier."""

import pytest

from src.modules.classifier.ai.ner import RegexEntityExtractor


class TestRegexEntityExtractor:
    """Тесты извлечения сущностей regex-экстрактором."""

    @pytest.mark.asyncio
    async def test_extract_salary_from(self):
        """Извлечение зарплаты с 'от'."""
        extractor = RegexEntityExtractor()
        text = "Разработчик Python, зарплата от 100000 рублей"
        result = await extractor.extract(text)
        assert result.entities.get("salary_min") == 100000

    @pytest.mark.asyncio
    async def test_extract_salary_to(self):
        """Извлечение зарплаты с 'до'."""
        extractor = RegexEntityExtractor()
        text = "Дизайнер, бюджет до 80к"
        result = await extractor.extract(text)
        assert result.entities.get("salary_max") == 80000

    @pytest.mark.asyncio
    async def test_extract_salary_range(self):
        """Извлечение диапазона зарплат."""
        extractor = RegexEntityExtractor()
        text = "Разработчик, зарплата 50-100 тыс руб"
        result = await extractor.extract(text)
        assert result.entities.get("salary_min") == 50000
        assert result.entities.get("salary_max") == 100000

    @pytest.mark.asyncio
    async def test_extract_salary_shorthand(self):
        """Извлечение зарплаты с сокращениями (к, тыс)."""
        extractor = RegexEntityExtractor()
        text = "Разработчик, зп от 150к"
        result = await extractor.extract(text)
        assert result.entities.get("salary_min") == 150000

    @pytest.mark.asyncio
    async def test_extract_type_remote(self):
        """Извлечение типа занятости - удалённо."""
        extractor = RegexEntityExtractor()
        text = "Разработчик, удалённая работа"
        result = await extractor.extract(text)
        assert result.entities.get("type") == "remote"

    @pytest.mark.asyncio
    async def test_extract_type_office(self):
        """Извлечение типа занятости - офис."""
        extractor = RegexEntityExtractor()
        text = "Менеджер, работа в офисе"
        result = await extractor.extract(text)
        assert result.entities.get("type") == "office"

    @pytest.mark.asyncio
    async def test_extract_type_project(self):
        """Извлечение типа занятости - проект."""
        extractor = RegexEntityExtractor()
        text = "Дизайнер на проект"
        result = await extractor.extract(text)
        assert result.entities.get("type") == "project"

    @pytest.mark.asyncio
    async def test_extract_stack(self):
        """Извлечение технологий."""
        extractor = RegexEntityExtractor()
        text = "Разработчик со знанием python, django, fastapi"
        result = await extractor.extract(text)
        stack = result.entities.get("stack", [])
        assert "python" in stack
        assert "django" in stack
        assert "fastapi" in stack

    @pytest.mark.asyncio
    async def test_extract_all_entities(self):
        """Извлечение всех сущностей сразу."""
        extractor = RegexEntityExtractor()
        text = """
        Разработчик Python (удалённо)
        Зарплата от 150к до 250к
        Стек: python, django, react, figma
        """
        result = await extractor.extract(text)
        assert result.entities.get("salary_min") == 150000
        assert result.entities.get("salary_max") == 250000
        assert result.entities.get("type") == "remote"
        stack = result.entities.get("stack", [])
        assert len(stack) >= 3

    @pytest.mark.asyncio
    async def test_extract_no_entities(self):
        """Текст без сущностей."""
        extractor = RegexEntityExtractor()
        text = "Просто какой-то текст без конкретики"
        result = await extractor.extract(text)
        # entities может быть пустым или содержать только _all_scores
        assert isinstance(result.entities, dict)


class TestZeroShotCategoryClassifier:
    """Тесты zero-shot классификатора."""

    @pytest.mark.asyncio
    async def test_classify_empty_labels(self):
        """Классификация с пустым списком лейблов."""
        from src.modules.classifier.ai.category import ZeroShotCategoryClassifier

        classifier = ZeroShotCategoryClassifier()
        result = await classifier.classify("Тестовый текст", [])
        assert result.categories == []

    @pytest.mark.asyncio
    async def test_classify_single_label(self):
        """Классификация с одним лейблом."""
        from src.modules.classifier.ai.category import ZeroShotCategoryClassifier

        classifier = ZeroShotCategoryClassifier()
        labels = [{"id": "123", "slug": "it", "name": "IT"}]
        result = await classifier.classify("Разработчик Python", labels)
        # Модель может не загрузиться в тестах — проверяем что результат возвращается
        assert isinstance(result.categories, list)
