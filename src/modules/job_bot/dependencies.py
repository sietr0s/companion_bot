"""
DI-зависимости модуля job_bot.

Фабрики для создания сервисов и репозиториев.
"""

from fastapi import Depends

from src.bus.interface import MessageBus
from src.bus.providers import get_message_bus
from src.modules.job_matcher.repository import (
    JobOfferRepository,
    SubscriptionRepository,
)
from src.modules.job_matcher.service import JobMatcherService


def get_job_offer_repository() -> JobOfferRepository:
    return JobOfferRepository()


def get_subscription_repository() -> SubscriptionRepository:
    return SubscriptionRepository()


def get_job_matcher_service(
    offer_repo: JobOfferRepository = Depends(get_job_offer_repository),
    sub_repo: SubscriptionRepository = Depends(get_subscription_repository),
    bus: MessageBus = Depends(get_message_bus),
) -> JobMatcherService:
    return JobMatcherService(offer_repo=offer_repo, sub_repo=sub_repo)
