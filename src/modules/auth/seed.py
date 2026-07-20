"""
Seed-функции для инициализации данных при старте приложения.

Создаёт admin-пользователя, если он ещё не существует.
Вызывается из lifespan-контекста main.py.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.bus.interface import MessageProducer
from src.core.config import settings
from src.core.exceptions import ConflictError
from src.modules.auth.repository import AuthRepository
from src.modules.auth.service import AuthService

logger = logging.getLogger(__name__)


async def seed_admin(session: AsyncSession, bus: MessageProducer) -> None:
    """
    Создать admin-пользователя при старте приложения.

    Проверяет, существует ли учётная запись с ADMIN_EMAIL.
    Если нет — создаёт через AuthService с ролью admin.
    """
    repo = AuthRepository()
    service = AuthService(repository=repo, message_bus=bus)

    # Проверяем, существует ли уже admin
    existing = await repo.get_by_identifier(session, settings.ADMIN_EMAIL)
    if existing:
        logger.info(
            "Admin-пользователь уже существует: %s (role=%s)",
            settings.ADMIN_EMAIL,
            existing.role,
        )
        return

    # Создаём admin-учётную запись
    try:
        await service.register(
            session,
            {
                "identifier": settings.ADMIN_EMAIL,
                "identifier_type": "email",
                "password": settings.ADMIN_PASSWORD,
                "role": "admin",
            },
        )
        logger.info(
            "Создан admin-пользователь: %s",
            settings.ADMIN_EMAIL,
        )
    except ConflictError:
        logger.info(
            "Admin-пользователь уже существует (конфликт): %s",
            settings.ADMIN_EMAIL,
        )
