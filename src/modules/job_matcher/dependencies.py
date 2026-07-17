"""
DI-зависимости модуля job_matcher.

Фабрики для внедрения JobMatcherService через FastAPI Depends.
"""

from fastapi import Depends

from src.bus.interface import MessageBus
from src.bus import get_producer
from src.modules.job_matcher.repository import (
    JobOfferRepository,
    SubscriptionRepository,
)
from src.modules.job_matcher.service import JobMatcherService


def get_job_offer_repository() -> JobOfferRepository:
    """Фабрика репозитория вакансий."""
    return JobOfferRepository()


def get_subscription_repository() -> SubscriptionRepository:
    """Фабрика репозитория подписок."""
    return SubscriptionRepository()


def get_job_matcher_service(
    offer_repo: JobOfferRepository = Depends(get_job_offer_repository),
    sub_repo: SubscriptionRepository = Depends(get_subscription_repository),
    bus: MessageBus = Depends(get_producer),
) -> JobMatcherService:
    """Фабрика сервиса подбора вакансий с внедрением репозиториев и шины."""
    return JobMatcherService(
        offer_repo=offer_repo,
        sub_repo=sub_repo,
        bus=bus,
    )


def get_job_matcher_service_factory(
    bus: MessageBus | None = None,
):
    """
    Фабрика (session, service) для обработчиков шины.

    Возвращает кортеж (session, JobMatcherService) для использования
    в обработчиках событий шины.

    Args:
        bus: Шина сообщений. Если None, используется шина по умолчанию.
    """
    return JobMatcherService(
        offer_repo=get_job_offer_repository(),
        sub_repo=get_subscription_repository(),
        bus=bus,
    )
