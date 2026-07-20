"""Сервис обработки вакансий модуля job_matcher."""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.filters import Filter
from src.base.service import BaseService
from src.bus.interface import MessageProducer
from src.core.bus_topics import BusTopics
from src.modules.job_matcher.models import JobOffer
from src.modules.job_matcher.repository import JobOfferRepository, SubscriptionRepository

logger = logging.getLogger(__name__)


class JobOfferService(BaseService[JobOfferRepository, JobOffer]):
    """Сохраняет, классифицирует и рассылает вакансии."""

    def __init__(
        self,
        offer_repo: JobOfferRepository,
        sub_repo: SubscriptionRepository,
        bus: MessageProducer,
    ) -> None:
        super().__init__(offer_repo)
        self._sub_repo = sub_repo
        self._bus = bus

    async def get_offers(
        self,
        session: AsyncSession,
        filters: list[Filter] | None = None,
        skip: int = 0,
        limit: int = 100,
        order_by: str | None = "-created_at",
    ) -> tuple[list[JobOffer], int]:
        """Получить вакансии для административного API."""
        return await self.repository.get_list(session, filters, skip, limit, order_by)

    async def save_job_offer(
        self,
        session: AsyncSession,
        text: str,
        chat_id: int,
        message_id: int,
        sender: dict,
    ) -> JobOffer:
        """Сохранить вакансию из Telegram."""
        job_offer = await self.repository.create(
            session,
            {
                "title": text[:500],
                "description": text,
                "location": None,
                "salary_from": None,
                "salary_to": None,
                "tags": None,
                "source_chat_id": chat_id,
                "source_message_id": message_id,
                "telegram_sender_id": sender.get("sender_id"),
                "telegram_username": sender.get("username"),
                "telegram_first_name": sender.get("first_name"),
                "telegram_last_name": sender.get("last_name"),
            },
        )
        logger.info("JobOffer сохранён: id=%s", job_offer.id)
        return job_offer

    async def send_for_classification(
        self,
        job_offer_id: uuid.UUID,
        text: str,
    ) -> None:
        """Отправить вакансию на классификацию."""
        await self._bus.publish(
            BusTopics.TEXT_CLASSIFY_REQUEST,
            {"request_id": str(job_offer_id), "text": text},
        )
        logger.info("JobOffer %s отправлен на классификацию", job_offer_id)

    async def update_job_offer_categories(
        self,
        session: AsyncSession,
        job_offer_id: uuid.UUID,
        category_ids: list,
    ) -> None:
        """Обновить категории вакансии после классификации."""
        job_offer = await self.repository.get_by_id(session, job_offer_id)
        if job_offer is None:
            logger.warning("JobOffer не найден: id=%s", job_offer_id)
            return

        normalized_ids = [
            str(uuid.UUID(value) if isinstance(value, str) else value)
            for value in category_ids
        ]
        await self.repository.update(
            session,
            job_offer,
            {"category_ids": normalized_ids or None},
        )
        logger.info("JobOffer %s обновлён категориями: %s", job_offer.id, normalized_ids)

    async def handle_offer_classified(
        self,
        session: AsyncSession,
        job_offer_id: uuid.UUID,
        category_ids: list[uuid.UUID] | None = None,
        tags: list[str] | None = None,
        salary_from: int | None = None,
        salary_to: int | None = None,
        location: str | None = None,
    ) -> None:
        """Найти подписчиков и отправить им полный текст вакансии."""
        job_offer = await self.repository.get_by_id(session, job_offer_id)
        if job_offer is None:
            logger.warning("JobOffer не найден: id=%s", job_offer_id)
            return

        matching_subs = await self._sub_repo.find_matching(
            session=session,
            category_ids=category_ids,
            tags=tags,
            salary_min=salary_from,
            salary_max=salary_to,
            location=location,
        )
        logger.info(
            "Оффер %s (категории: %s): найдено %d подходящих подписок",
            job_offer_id,
            category_ids,
            len(matching_subs),
        )

        offer_text = job_offer.description or job_offer.title
        for subscription in matching_subs:
            await self._bus.publish(
                BusTopics.NOTIFICATION_SEND,
                {
                    "auth_id": str(subscription.auth_id),
                    "template_name": "job_offer",
                    "channel": "telegram",
                    "body": {
                        "offer_text": offer_text,
                        "telegram_sender_id": job_offer.telegram_sender_id,
                        "telegram_username": job_offer.telegram_username,
                        "telegram_first_name": job_offer.telegram_first_name,
                        "telegram_last_name": job_offer.telegram_last_name,
                    },
                },
            )
