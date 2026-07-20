"""Public API job_matcher для авторизованной административной панели."""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.filters import parse_filters
from src.base.schemas import PaginatedResponse
from src.core.dependencies import get_current_admin, get_db_session
from src.modules.job_matcher.dependencies import (
    get_job_matcher_user_service,
    get_job_offer_service,
    get_subscription_service,
)
from src.modules.job_matcher.schemas.public import JobOfferAdminRead, SubscriptionAdminRead
from src.modules.job_matcher.services import (
    JobMatcherUserService,
    JobOfferService,
    SubscriptionService,
)

router = APIRouter(prefix="/api/v1/public/job-matcher", tags=["Job Matcher"])

SUBSCRIPTION_FILTER_FIELDS = {"id", "auth_id", "is_active", "created_at", "updated_at"}
OFFER_FILTER_FIELDS = {
    "id",
    "title",
    "location",
    "source_chat_id",
    "source_message_id",
    "created_at",
    "updated_at",
}


@router.get(
    "/subscriptions",
    response_model=PaginatedResponse[SubscriptionAdminRead],
    summary="Получить подписки для администратора",
)
async def get_subscriptions_admin(
    filters: list[str] = Query(default_factory=list, description="field+operator+value"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=100, ge=1, le=500),
    order_by: str = Query(default="-created_at", description="Поле сортировки; '-' = DESC"),
    _admin_id: uuid.UUID = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
    service: SubscriptionService = Depends(get_subscription_service),
) -> PaginatedResponse[SubscriptionAdminRead]:
    """Вернуть подписки только авторизованному администратору."""
    parsed = parse_filters(filters, allowed_fields=SUBSCRIPTION_FILTER_FIELDS)
    subscriptions, total = await service.get_subscriptions(
        session,
        filters=parsed,
        skip=(page - 1) * limit,
        limit=limit,
        order_by=order_by,
    )
    return PaginatedResponse.from_list(
        subscriptions,
        total,
        page=page,
        page_size=limit,
    )


@router.get(
    "/offers",
    response_model=PaginatedResponse[JobOfferAdminRead],
    summary="Получить вакансии для администратора",
)
async def get_offers_admin(
    filters: list[str] = Query(default_factory=list, description="field+operator+value"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=500),
    order_by: str = Query(default="-created_at", description="Поле сортировки; '-' = DESC"),
    _admin_id: uuid.UUID = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
    service: JobOfferService = Depends(get_job_offer_service),
) -> PaginatedResponse[JobOfferAdminRead]:
    """Вернуть сохранённые вакансии авторизованному администратору."""
    parsed = parse_filters(filters, allowed_fields=OFFER_FILTER_FIELDS)
    offers, total = await service.get_offers(
        session,
        filters=parsed,
        skip=(page - 1) * limit,
        limit=limit,
        order_by=order_by,
    )
    return PaginatedResponse.from_list(offers, total, page=page, page_size=limit)


@router.delete(
    "/users/{auth_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить пользователя и его подписку",
)
async def delete_user_admin(
    auth_id: uuid.UUID,
    _admin_id: uuid.UUID = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
    service: JobMatcherUserService = Depends(get_job_matcher_user_service),
) -> None:
    """Удалить подписку и через межмодульные клиенты удалить user и auth."""
    await service.delete_user(session, auth_id)
