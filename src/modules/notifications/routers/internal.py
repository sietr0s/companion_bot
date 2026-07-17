"""
Внутренние роуты модуля notifications.

Доступны только внутри кластера (network-level).
Отправка уведомлений по имени шаблона.
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db_session
from src.core.exceptions import NotFoundError
from src.modules.notifications.dependencies import get_notification_service
from src.modules.notifications.schemas.internal import SendNotificationRequest
from src.modules.notifications.service import NotificationService

router = APIRouter()


@router.post(
    "/send",
    response_model=SendNotificationRequest,
    status_code=status.HTTP_201_CREATED,
    summary="[Internal] Отправить уведомление по шаблону",
)
async def send_notification(
    data: SendNotificationRequest,
    session: AsyncSession = Depends(get_db_session),
    service: NotificationService = Depends(get_notification_service),
):
    """
    Отправить уведомление по имени шаблона.

    Используется для межмодульного взаимодействия.
    """
    log = await service.send_notification(
        session=session,
        auth_id=data.auth_id,
        template_name=data.template_name,
        channel=data.channel,
        body=data.body,
    )
    return log


@router.post(
    "/templates/{template_id}/render",
    summary="[Internal] Тестовый рендер шаблона",
)
async def render_template_test(
    template_id: uuid.UUID,
    test_data: dict = None,
    session: AsyncSession = Depends(get_db_session),
    service: NotificationService = Depends(get_notification_service),
) -> dict:
    """
    Тестовый рендер шаблона с данными.

    Возвращает rendered subject и body без отправки.
    """
    from src.modules.notifications.template_engine import find_template, render

    if test_data is None:
        test_data = {}
    template_data = await find_template(session, str(template_id), None)
    if not template_data:
        raise NotFoundError(detail="Шаблон не найден")

    test_data = test_data or {}

    subject = ""
    if template_data.get("subject_template"):
        subject = render(template_data["subject_template"], test_data)

    body = render(template_data["body_template"], test_data)

    return {
        "template_id": str(template_id),
        "subject": subject,
        "body": body,
    }
