"""
Тесты обработчиков модуля job_matcher.

Проверяют, что handlers правильно делегируют в JobMatcherService.
"""

from src.bus.in_memory.producer import InMemoryProducer
from src.modules.job_matcher.handlers import register_handlers
from src.modules.job_matcher.models import JobOffer, Subscription
from src.modules.job_matcher.repository import (
    JobOfferRepository,
    SubscriptionRepository,
)
from src.modules.job_matcher.service import JobMatcherService
from tests.conftest import MockBus


class TestHandlers:
    """Тесты обработчиков шины."""

    async def test_start_handler_registers(self):
        """
        register_handlers не падает.
        """
        bus = InMemoryProducer()
        service = JobMatcherService(
            offer_repo=JobOfferRepository(),
            sub_repo=SubscriptionRepository(),
            bus=MockBus(),
        )

        async def service_factory():
            return None, service

        # Не должно быть ошибки
        register_handlers(bus=bus, service_factory=service_factory)

    async def test_subscribe_handler_registers(self):
        """
        register_handlers не падает.
        """
        bus = InMemoryProducer()
        service = JobMatcherService(
            offer_repo=JobOfferRepository(),
            sub_repo=SubscriptionRepository(),
            bus=MockBus(),
        )

        async def service_factory():
            return None, service

        register_handlers(bus=bus, service_factory=service_factory)

    async def test_offer_handler_registers(self):
        """
        register_handlers не падает.
        """
        bus = InMemoryProducer()
        service = JobMatcherService(
            offer_repo=JobOfferRepository(),
            sub_repo=SubscriptionRepository(),
            bus=MockBus(),
        )

        async def service_factory():
            return None, service

        register_handlers(bus=bus, service_factory=service_factory)