"""
Тесты обработки команды /start.

Проверяют, что при /start создаётся учётная запись (Auth)
и профиль пользователя (User) через клиенты.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.repository import AuthRepository
from src.modules.job_matcher.models import JobOffer, Subscription
from src.modules.job_matcher.repository import (
    JobOfferRepository,
    SubscriptionRepository,
)
from src.modules.job_matcher.service import JobMatcherService
from src.modules.users.repository import UserRepository
from tests.conftest import MockBus


class TestStartCommand:
    """Тесты команды /start — регистрация пользователя."""

    async def test_start_creates_auth_and_user(
        self,
        db_session: AsyncSession,
    ):
        """
        При /start создаётся учётная запись в Auth и профиль в User.

        Проверяем через репозитории, что записи реально в БД.
        """
        # Arrange
        chat_id = 888888
        mock_bus = MockBus()
        service = JobMatcherService(
            offer_repo=JobOfferRepository(),
            sub_repo=SubscriptionRepository(),
            bus=mock_bus,
        )

        # Act — вызываем handle_start
        await service.handle_start(session=db_session, chat_id=chat_id)

        # Assert — проверяем, что событие опубликовано
        assert len(mock_bus.published) > 0
        assert mock_bus.published[0][0] == "bot.message.outgoing"
        assert "Добро пожаловать" in mock_bus.published[0][1]["text"]

        # Assert — проверяем, что Auth создан
        auth_repo = AuthRepository()
        auth_account = await auth_repo.get_by_identifier(db_session, f"tg_{chat_id}")
        assert auth_account is not None
        assert auth_account.identifier == f"tg_{chat_id}"
        assert auth_account.identifier_type == "telegram"

        # Assert — проверяем, что User создан
        user_repo = UserRepository()
        profile = await user_repo.get_by_auth_id(db_session, auth_account.id)
        assert profile is not None
        assert profile.auth_id == auth_account.id

    async def test_start_creates_subscription(
        self,
        db_session: AsyncSession,
    ):
        """
        При /start создаётся подписка (Subscription).

        Сначала регистрирует пользователя через /start,
        затем вызывает /subscribe — проверяет, что
        подписка создаётся с правильным auth_id.
        """
        # Arrange — сначала регистрируем через /start
        chat_id = 888888
        mock_bus = MockBus()
        service = JobMatcherService(
            offer_repo=JobOfferRepository(),
            sub_repo=SubscriptionRepository(),
            bus=mock_bus,
        )

        await service.handle_start(session=db_session, chat_id=chat_id)

        # Получаем auth_id из созданной записи
        auth_repo = AuthRepository()
        auth_account = await auth_repo.get_by_identifier(db_session, f"tg_{chat_id}")
        assert auth_account is not None

        # Act — вызываем handle_subscribe
        mock_bus.published.clear()
        await service.handle_subscribe(session=db_session, chat_id=chat_id)

        # Assert — проверяем, что подписка создана с правильным auth_id
        repo = SubscriptionRepository()
        sub = await repo.get_by_auth_id(session=db_session, auth_id=auth_account.id)
        assert sub is not None
        assert sub.auth_id == auth_account.id
        assert sub.is_active is True

    async def test_start_already_registered(
        self,
        db_session: AsyncSession,
    ):
        """
        Повторный /start не создаёт дубликата.

        Если пользователь уже зарегистрирован в Auth —
        выводится сообщение "Вы уже зарегистрированы".
        """
        # Arrange — создаём Auth запись
        from src.modules.auth.repository import AuthRepository

        auth_repo = AuthRepository()
        account = await auth_repo.create(
            db_session,
            {
                "identifier": "tg_777777",
                "identifier_type": "telegram",
                "hashed_password": "hashed",
            },
        )

        mock_bus = MockBus()
        service = JobMatcherService(
            offer_repo=JobOfferRepository(),
            sub_repo=SubscriptionRepository(),
            bus=mock_bus,
        )

        # Act — повторный вызов
        await service.handle_start(session=db_session, chat_id=777777)

        # Assert — сообщение о том, что уже зарегистрирован
        assert len(mock_bus.published) > 0
        assert "уже зарегистрированы" in mock_bus.published[0][1]["text"]
