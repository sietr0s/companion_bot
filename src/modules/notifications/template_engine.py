"""
Jinja2-движок рендеринга шаблонов.

Ищет шаблон сначала в БД, потом в файловой системе.
Если не найден — возвращает None.
"""

import logging
import os

from jinja2 import Template
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.modules.notifications.repository import NotificationTemplateRepository

logger = logging.getLogger(__name__)


async def find_template(
    session: AsyncSession,
    name: str,
    channel: str = "email",
) -> dict | None:
    """
    Найти шаблон: сначала в БД, потом в файлах.

    Возвращает dict с ключами subject_template и body_template,
    либо None если шаблон не найден.
    """
    # 1. Ищем в БД
    repo = NotificationTemplateRepository()
    db_template = await repo.get_by_name(session, name, channel)
    if db_template:
        return {
            "subject_template": db_template.subject_template,
            "body_template": db_template.body_template,
            "source": "db",
        }

    # 2. Ищем в файлах
    templates_dir = settings.TEMPLATES_DIR
    file_path = os.path.join(templates_dir, channel, f"{name}.j2")
    if os.path.exists(file_path):
        with open(file_path) as f:
            body_template = f.read()

        # Ищем отдельный файл с темой
        subject_path = os.path.join(templates_dir, channel, f"{name}_subject.j2")
        subject_template = None
        if os.path.exists(subject_path):
            with open(subject_path) as f:
                subject_template = f.read()

        return {
            "subject_template": subject_template,
            "body_template": body_template,
            "source": "file",
        }

    logger.warning("Шаблон не найден: name=%s, channel=%s", name, channel)
    return None


def render(template_str: str, context: dict) -> str:
    """Рендерит Jinja2-шаблон с контекстом."""
    template = Template(template_str)
    return template.render(**context)
