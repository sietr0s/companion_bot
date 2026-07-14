"""
Сервис бизнес-логики для подбора предложений о работе.

Не содержит HTTP-роуты — только обработчики шины.
Использует репозитории для работы с БД.
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.service import BaseService
from src.bus.interface import MessageBus
from src.core.bus_topics import BusTopics
from src.core.clients.auth_client import AuthClient
from src.core.clients.users_client import UsersClient
from src.modules.job_matcher.models import JobOffer
from src.modules.job_matcher.repository import (
    JobOfferRepository,
    SubscriptionRepository,
)

logger = logging.getLogger(__name__)


class JobMatcherService(BaseService[JobOfferRepository]):
    """
    Сервис для подбора предложений.

    Получает job.offer.classified → ищет подходящие подписки.
    """

    def __init__(
        self,
        offer_repo: JobOfferRepository,
        sub_repo: SubscriptionRepository,
        bus: MessageBus,
    ) -> None:
        super().__init__(offer_repo)
        self._sub_repo = sub_repo
        self._bus = bus

    async def save_job_offer(
        self,
        session: AsyncSession,
        text: str,
        chat_id: int,
    ) -> JobOffer:
        """
        Сохранить вакансию из Telegram.

        Returns:
            Созданный JobOffer с ID.
        """
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
                "source_message_id": 0,
            },
        )
        logger.info("JobOffer сохранён: id=%s", job_offer.id)
        return job_offer

    async def send_for_classification(
        self,
        job_offer_id: uuid.UUID,
        text: str,
    ) -> None:
        """
        Отправить вакансию на классификацию.

        Публикует событие TEXT_CLASSIFY_REQUEST с job_offer.id как request_id.
        """
        await self._bus.publish(
            BusTopics.TEXT_CLASSIFY_REQUEST,
            {
                "request_id": str(job_offer_id),
                "text": text,
            },
        )
        logger.info("JobOffer %s отправлен на классификацию", job_offer_id)

    async def update_job_offer_categories(
        self,
        session: AsyncSession,
        job_offer_id: uuid.UUID,
        category_ids: list,
    ) -> None:
        """
        Обновить категории у вакансии после классификации.
        """
        # Находим JobOffer по id через репозиторий
        job_offer = await self.repository.get_by_id(session, job_offer_id)

        if not job_offer:
            logger.warning("JobOffer не найден: id=%s", job_offer_id)
            return

        uuid_objects = [
            uuid.UUID(cat_id) if isinstance(cat_id, str) else cat_id for cat_id in category_ids
        ]
        # Сохраняем как строки для JSON сериализации
        category_ids = [str(cat_id) for cat_id in uuid_objects]

        # Обновляем вакансию через репозиторий
        await self.repository.update(
            session, job_offer, {"category_ids": category_ids if category_ids else None}
        )
        logger.info(
            "JobOffer %s обновлён категориями: %s",
            job_offer.id,
            category_ids,
        )

    async def handle_start(
        self,
        session: AsyncSession,
        chat_id: int,
    ) -> None:
        """
        Обработка команды /start.

        Проверяет, зарегистрирован ли пользователь.
        Если нет — создаёт учётную запись и профиль.
        """
        auth_client = AuthClient()

        # Проверяем, зарегистрирован ли пользователь в Auth
        existing_auth_id = await auth_client.get_by_identifier(
            identifier=f"tg_{chat_id}",
            session=session,
        )
        if existing_auth_id:
            logger.info("Пользователь уже зарегистрирован: chat_id=%s", chat_id)
            await self._bus.publish(
                BusTopics.BOT_MESSAGE_OUTGOING,
                {
                    "chat_id": chat_id,
                    "text": "Вы уже зарегистрированы! /subscribe — подписаться на предложения",
                },
            )
            return

        users_client = UsersClient()

        auth_id = await auth_client.register(
            identifier=f"tg_{chat_id}",
            identifier_type="telegram",
            session=session,
        )
        await users_client.create_profile(
            auth_id=auth_id,
            session=session,
        )
        logger.info("Пользователь зарегистрирован: auth_id=%s", auth_id)
        await self._bus.publish(
            BusTopics.BOT_MESSAGE_OUTGOING,
            {
                "chat_id": chat_id,
                "text": "Добро пожаловать! Используйте /subscribe для подписки на предложения",
            },
        )

    async def handle_subscribe(
        self,
        session: AsyncSession,
        chat_id: int,
    ) -> None:
        """
        Обработка команды /subscribe.

        Проверяет, зарегистрирован ли пользователь в Auth.
        Если нет — сообщает об ошибке.
        """
        auth_client = AuthClient()

        # Проверяем, зарегистрирован ли пользователь в Auth
        existing_auth_id = await auth_client.get_by_identifier(
            identifier=f"tg_{chat_id}",
            session=session,
        )

        if not existing_auth_id:
            logger.warning(
                "Пользователь не зарегистрирован: /subscribe без /start, chat_id=%s",
                chat_id,
            )
            await self._bus.publish(
                BusTopics.BOT_MESSAGE_OUTGOING,
                {
                    "chat_id": chat_id,
                    "text": "Сначала зарегистрируйтесь: /start",
                },
            )
            return

        # Создаём подписку через репозиторий
        await self._sub_repo.create(
            session,
            {"auth_id": existing_auth_id, "is_active": True},
        )

        logger.info("Подписка создана: auth_id=%s", existing_auth_id)

        await self._bus.publish(
            BusTopics.BOT_MESSAGE_OUTGOING,
            {
                "chat_id": chat_id,
                "text": "Подписка создана! Будем присылать подходящие предложения",
            },
        )

    async def handle_offer_classified(
        self,
        session: AsyncSession,
        title: str,
        category_ids: list[uuid.UUID] | None = None,
        tags: list[str] | None = None,
        salary_from: int | None = None,
        salary_to: int | None = None,
        location: str | None = None,
    ) -> None:
        """
        Обработка классифицированного оффера.

        Ищет подходящие подписки по категориям и отправляет уведомления.
        """
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
            title,
            category_ids,
            len(matching_subs),
        )

        for sub in matching_subs:
            await self._bus.publish(
                BusTopics.NOTIFICATION_SEND,
                {
                    "auth_id": str(sub.auth_id),
                    "template_name": "job_offer",
                    "channel": "telegram",
                    "body": {
                        "title": title,
                        "tags": tags,
                        "salary_from": salary_from,
                        "salary_to": salary_to,
                        "location": location,
                    },
                },
            )
