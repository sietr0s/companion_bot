"""
Сервис модуля нотификаций.

Управляет шаблонами, историей и отправкой уведомлений.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.filters import Filter
from src.base.service import BaseService
from src.core.clients.users_client import UsersClient
from src.core.exceptions import NotFoundError
from src.modules.notifications.constants import NotificationChannel, NotificationStatus
from src.modules.notifications.models import NotificationLog, NotificationTemplate
from src.modules.notifications.providers.base import NotificationProvider
from src.modules.notifications.repository import (
    NotificationLogRepository,
    NotificationTemplateRepository,
)
from src.modules.notifications.template_engine import find_template, render


class NotificationService(BaseService[NotificationTemplateRepository]):
    """
    Сервис управления уведомлениями.

    Координирует работу с шаблонами, провайдерами и логами.
    """

    def __init__(
        self,
        template_repo: NotificationTemplateRepository,
        log_repo: NotificationLogRepository,
        provider: NotificationProvider,
    ) -> None:
        super().__init__(template_repo)
        self.log_repo = log_repo
        self.provider = provider

    # --- Шаблоны ---

    async def create_template(self, session: AsyncSession, data: dict) -> NotificationTemplate:
        """Создать шаблон уведомления."""
        return await self.repository.create(session, data)

    async def get_template(
        self, session: AsyncSession, template_id: uuid.UUID
    ) -> NotificationTemplate:
        """Получить шаблон по ID."""
        template = await self.repository.get_by_id(session, template_id)
        if not template:
            raise NotFoundError(detail="Шаблон не найден")
        return template

    async def get_templates(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        filters: list[Filter] | None = None,
    ) -> tuple[list[NotificationTemplate], int]:
        """Получить список шаблонов с фильтрацией и пагинацией."""
        return await self.repository.get_list(session, filters, skip, limit)

    async def update_template(
        self,
        session: AsyncSession,
        template_id: uuid.UUID,
        data: dict,
    ) -> NotificationTemplate:
        """Обновить шаблон."""
        template = await self.get_template(session, template_id)
        return await self.repository.update(session, template, data)

    async def delete_template(self, session: AsyncSession, template_id: uuid.UUID) -> None:
        """Удалить шаблон."""
        template = await self.get_template(session, template_id)
        await self.repository.delete(session, template)

    # --- История ---

    async def get_history(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        filters: list[Filter] | None = None,
    ) -> tuple[list[NotificationLog], int]:
        """Получить историю уведомлений с фильтрацией и пагинацией."""
        return await self.log_repo.get_list(session, filters, skip, limit)

    # --- Отправка ---

    async def send_notification(
        self,
        session: AsyncSession,
        auth_id: uuid.UUID,
        template_name: str,
        channel: str,
        body: dict,
    ) -> NotificationLog:
        """
        Отправить уведомление.

        1. Резолвим email по auth_id через UsersClient (для email-канала)
        2. Найти шаблон (БД → файлы)
        3. Рендерить Jinja2
        4. Отправить через провайдер
        5. Сохранить в лог
        """
        # Резолвим email по auth_id
        client = UsersClient()
        recipient = await client.resolve_email_by_auth_id(auth_id)

        # Ищем шаблон
        template_data = await find_template(session, template_name, channel)

        subject = ""
        rendered_body = ""

        if template_data:
            # Рендерим тело
            rendered_body = render(template_data["body_template"], body)

            # Рендерим тему (если есть)
            if template_data.get("subject_template"):
                subject = render(template_data["subject_template"], body)
        else:
            # Шаблон не найден — используем body как есть
            rendered_body = str(body)
            subject = template_name

        # Отправляем через провайдер
        status = NotificationStatus.SENT
        error_message = None
        try:
            await self.provider.send(recipient, subject, rendered_body)
        except Exception as e:
            status = NotificationStatus.FAILED
            error_message = str(e)

        # Сохраняем в лог
        log = await self.log_repo.create(
            session,
            {
                "auth_id": auth_id,
                "channel": channel,
                "template_name": template_name,
                "recipient": recipient,
                "subject": subject,
                "body": rendered_body,
                "status": status,
                "error_message": error_message,
            },
        )

        return log
