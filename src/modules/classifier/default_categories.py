"""Категории по умолчанию для модуля classifier."""

from dataclasses import dataclass


@dataclass
class DefaultCategory:
    """Категория по умолчанию."""

    name: str
    slug: str
    description: str | None = None


# Список категорий по умолчанию
# Создаются при первом запуске приложения
DEFAULT_CATEGORIES: list[DefaultCategory] = [
    DefaultCategory(
        name="Backend-разработка",
        slug="backend",
        description="Разработка серверной части, API, баз данных",
    ),
    DefaultCategory(
        name="Frontend-разработка",
        slug="frontend",
        description="Разработка клиентской части, веб-интерфейсов",
    ),
    DefaultCategory(
        name="Fullstack-разработка",
        slug="fullstack",
        description="Универсальные разработчики (frontend + backend)",
    ),
    DefaultCategory(
        name="Мобильная разработка",
        slug="mobile",
        description="Разработка мобильных приложений (iOS, Android)",
    ),
    DefaultCategory(
        name="DevOps, SRE",
        slug="devops",
        description="Инфраструктура, CI/CD, мониторинг, облака",
    ),
    DefaultCategory(
        name="Data Science, ML, AI",
        slug="data_science",
        description="Анализ данных, машинное обучение, нейросети",
    ),
    DefaultCategory(
        name="Дизайн, UX/UI",
        slug="design",
        description="Проектирование интерфейсов, графический дизайн",
    ),
    DefaultCategory(
        name="Менеджмент проектов",
        slug="management",
        description="Управление проектами, продуктом, командой",
    ),
    DefaultCategory(
        name="Тестирование, QA",
        slug="qa",
        description="Контроль качества, автоматизация тестирования",
    ),
    DefaultCategory(
        name="Аналитика",
        slug="analytics",
        description="Бизнес-анализ, системный анализ, аналитика данных",
    ),
]
