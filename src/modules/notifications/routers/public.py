"""
Публичные роуты модуля notifications.

CRUD шаблонов и отправка уведомлений.
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.filters import parse_filters
from src.base.schemas import PaginatedResponse
from src.core.dependencies import get_current_admin, get_db_session
from src.core.exceptions import NotFoundError
from src.modules.notifications.dependencies import get_notification_service
from src.modules.notifications.schemas.public import (
    NotificationLogRead,
    TemplateCreate,
    TemplateRead,
    TemplateUpdate,
)
from src.modules.notifications.service import NotificationService

router = APIRouter(prefix="/api/v1/public/notifications", tags=["Notifications"])

TEMPLATE_FILTER_FIELDS = {
    "id",
    "name",
    "channel",
    "is_active",
    "created_at",
    "updated_at",
}
LOG_FILTER_FIELDS = {
    "id",
    "auth_id",
    "channel",
    "template_name",
    "recipient",
    "status",
    "created_at",
    "updated_at",
}


# --- Шаблоны ---


@router.post(
    "/templates/",
    response_model=TemplateRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать шаблон уведомления",
)
async def create_template(
    data: TemplateCreate,
    admin_id: uuid.UUID = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
    service: NotificationService = Depends(get_notification_service),
) -> TemplateRead:
    """Создать шаблон уведомления."""
    return await service.create_template(session, data.model_dump())


@router.get(
    "/templates/",
    response_model=PaginatedResponse[TemplateRead],
    summary="Список шаблонов",
)
async def get_templates(
    filters: list[str] = Query(default_factory=list, description="field+operator+value"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=100, ge=1, le=500),
    order_by: str = Query(default="-created_at", description="Поле сортировки; '-' = DESC"),
    admin_id: uuid.UUID = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
    service: NotificationService = Depends(get_notification_service),
) -> PaginatedResponse:
    """Получить список шаблонов с фильтрацией и пагинацией."""
    parsed = parse_filters(filters, allowed_fields=TEMPLATE_FILTER_FIELDS)
    skip = (page - 1) * limit
    templates, total = await service.get_templates(session, skip, limit, parsed, order_by)
    return PaginatedResponse.from_list(templates, total, page=page, page_size=limit)


@router.get(
    "/templates/{template_id}",
    response_model=TemplateRead,
    summary="Получить шаблон по ID",
)
async def get_template(
    template_id: uuid.UUID,
    admin_id: uuid.UUID = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
    service: NotificationService = Depends(get_notification_service),
) -> TemplateRead:
    """Получить шаблон по ID."""
    return await service.get_template(session, template_id)


@router.patch(
    "/templates/{template_id}",
    response_model=TemplateRead,
    summary="Обновить шаблон",
)
async def update_template(
    template_id: uuid.UUID,
    data: TemplateUpdate,
    admin_id: uuid.UUID = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
    service: NotificationService = Depends(get_notification_service),
) -> TemplateRead:
    """Обновить шаблон."""
    return await service.update_template(session, template_id, data.model_dump(exclude_unset=True))


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить шаблон",
)
async def delete_template(
    template_id: uuid.UUID,
    admin_id: uuid.UUID = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
    service: NotificationService = Depends(get_notification_service),
) -> None:
    """Удалить шаблон."""
    await service.delete_template(session, template_id)


# --- История ---


@router.get(
    "/history/",
    response_model=PaginatedResponse[NotificationLogRead],
    summary="История уведомлений",
)
async def get_history(
    filters: list[str] = Query(default_factory=list, description="field+operator+value"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    order_by: str = Query(default="-created_at", description="Поле сортировки; '-' = DESC"),
    admin_id: uuid.UUID = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
    service: NotificationService = Depends(get_notification_service),
) -> PaginatedResponse:
    """Получить историю уведомлений с фильтрацией и пагинацией."""
    parsed = parse_filters(filters, allowed_fields=LOG_FILTER_FIELDS)
    skip = (page - 1) * limit
    logs, total = await service.get_history(session, skip, limit, parsed, order_by)
    return PaginatedResponse.from_list(logs, total, page=page, page_size=limit)


@router.get(
    "/history/{log_id}",
    response_model=NotificationLogRead,
    summary="Детальный просмотр лога уведомления",
)
async def get_history_entry(
    log_id: uuid.UUID,
    admin_id: uuid.UUID = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationLogRead:
    """Получить детальную информацию о уведомлении."""
    log = await service.log_repo.get_by_id(session, log_id)
    if not log:
        raise NotFoundError(detail="Лог уведомления не найден")
    return NotificationLogRead.model_validate(log)
