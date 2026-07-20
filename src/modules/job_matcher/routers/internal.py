"""Internal API подписок job_matcher для административного интерфейса."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.filters import parse_filters
from src.base.schemas import PaginatedResponse
from src.core.dependencies import get_db_session
from src.core.internal_auth import require_internal_service_key
from src.modules.job_matcher.dependencies import get_subscription_service
from src.modules.job_matcher.schemas.internal import SubscriptionRead
from src.modules.job_matcher.services import SubscriptionService

router = APIRouter(
    prefix="/internal/job-matcher",
    tags=["Internal"],
    dependencies=[Depends(require_internal_service_key)],
)

FILTER_FIELDS = {"id", "auth_id", "is_active", "created_at", "updated_at"}


@router.get(
    "/subscriptions",
    response_model=PaginatedResponse[SubscriptionRead],
    summary="[Internal] Получить подписки пользователей",
)
async def get_subscriptions(
    filters: list[str] = Query(default_factory=list, description="field+operator+value"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=100, ge=1, le=500),
    order_by: str = Query(default="-created_at", description="Поле сортировки; '-' = DESC"),
    session: AsyncSession = Depends(get_db_session),
    service: SubscriptionService = Depends(get_subscription_service),
) -> PaginatedResponse[SubscriptionRead]:
    """Вернуть подписки для объединения с пользователями по auth_id."""
    parsed = parse_filters(filters, allowed_fields=FILTER_FIELDS)
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
