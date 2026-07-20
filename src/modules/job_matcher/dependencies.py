"""
DI-зависимости модуля job_matcher.

Фабрики сервисов, разделённых по ответственности.
"""

from fastapi import Depends

from src.bus import get_producer
from src.modules.job_matcher.repository import (
    JobOfferRepository,
    SubscriptionRepository,
)
from src.modules.job_matcher.services import (
    JobMatcherUserService,
    JobOfferService,
    SubscriptionService,
)


def get_job_offer_repository() -> JobOfferRepository:
    """Фабрика репозитория вакансий."""
    return JobOfferRepository()


def get_subscription_repository() -> SubscriptionRepository:
    """Фабрика репозитория подписок."""
    return SubscriptionRepository()


def get_job_offer_service(
    offer_repo: JobOfferRepository = Depends(get_job_offer_repository),
    sub_repo: SubscriptionRepository = Depends(get_subscription_repository),
) -> JobOfferService:
    """Фабрика сервиса вакансий."""
    return JobOfferService(
        offer_repo=offer_repo,
        sub_repo=sub_repo,
        bus=get_producer(),
    )


def get_subscription_service(
    repository: SubscriptionRepository = Depends(get_subscription_repository),
) -> SubscriptionService:
    """Фабрика сервиса подписок."""
    return SubscriptionService(repository=repository, bus=get_producer())


def get_job_matcher_user_service(
    repository: SubscriptionRepository = Depends(get_subscription_repository),
) -> JobMatcherUserService:
    """Фабрика сервиса пользователей job_matcher."""
    return JobMatcherUserService(
        subscription_repository=repository,
        bus=get_producer(),
    )


def get_job_offer_service_factory() -> JobOfferService:
    """Создать сервис вакансий для обработчика шины."""
    return JobOfferService(
        offer_repo=get_job_offer_repository(),
        sub_repo=get_subscription_repository(),
        bus=get_producer(),
    )


def get_subscription_service_factory() -> SubscriptionService:
    """Создать сервис подписок для обработчика шины."""
    return SubscriptionService(
        repository=get_subscription_repository(),
        bus=get_producer(),
    )


def get_job_matcher_user_service_factory() -> JobMatcherUserService:
    """Создать сервис пользователей для обработчика шины."""
    return JobMatcherUserService(
        subscription_repository=get_subscription_repository(),
        bus=get_producer(),
    )
