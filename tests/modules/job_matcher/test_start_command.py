"""
Тесты обработки команды /start.

Проверяют, что при /start создаётся учётная запись (Auth)
и профиль пользователя (User) через клиенты.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.bus_topics import BusTopics
from src.modules.auth.repository import AuthRepository
from src.modules.classifier.repository import CategoryRepository
from src.modules.job_bot.schemas.events import TelegramUserInfo
from src.modules.job_matcher.repository import SubscriptionRepository
from src.modules.job_matcher.services import JobMatcherUserService, SubscriptionService
from src.modules.users.repository import TelegramRepository, UserRepository
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
        service = JobMatcherUserService(
            subscription_repository=SubscriptionRepository(),
            bus=mock_bus,
        )

        # Act — вызываем handle_start
        telegram_user = TelegramUserInfo(
            telegram_id=999001,
            username="ivanov",
            first_name="Иван",
            last_name="Иванов",
        )
        await service.handle_start(
            session=db_session,
            chat_id=chat_id,
            telegram_user=telegram_user,
        )

        # Assert — проверяем, что событие опубликовано
        assert len(mock_bus.published) > 0
        assert mock_bus.published[0][0] == "job_bot.command.send_message"
        assert "Добро пожаловать" in mock_bus.published[0][1]["text"]

        # Assert — проверяем, что Auth создан
        auth_repo = AuthRepository()
        auth_account = await auth_repo.get_by_identifier(
            db_session, f"tg_{telegram_user.telegram_id}"
        )
        assert auth_account is not None
        assert auth_account.identifier == f"tg_{telegram_user.telegram_id}"
        assert auth_account.identifier_type == "telegram"

        # Assert — проверяем, что User создан
        user_repo = UserRepository()
        profile = await user_repo.get_by_auth_id(db_session, auth_account.id)
        assert profile is not None
        assert profile.auth_id == auth_account.id
        assert profile.first_name == "Иван"
        assert profile.last_name == "Иванов"

        telegram = await TelegramRepository().get_by_auth_id(db_session, auth_account.id)
        assert telegram is not None
        assert telegram.telegram_id == str(telegram_user.telegram_id)
        assert telegram.telegram_username == telegram_user.username
        assert telegram.telegram_first_name == telegram_user.first_name
        assert telegram.telegram_last_name == telegram_user.last_name

    async def test_subscribe_offers_categories_and_creates_selected_subscription(
        self,
        db_session: AsyncSession,
    ):
        """
        /subscribe предлагает категории, а выбор создаёт Subscription.

        Сначала регистрирует пользователя через /start,
        затем вызывает /subscribe — проверяет, что
        подписка создаётся с правильным auth_id.
        """
        # Arrange — сначала регистрируем через /start
        chat_id = 888888
        mock_bus = MockBus()
        user_service = JobMatcherUserService(
            subscription_repository=SubscriptionRepository(),
            bus=mock_bus,
        )
        subscription_service = SubscriptionService(
            repository=SubscriptionRepository(),
            bus=mock_bus,
        )

        telegram_user = TelegramUserInfo(
            telegram_id=999002,
            username="subscriber",
            first_name="Пётр",
        )
        await user_service.handle_start(
            session=db_session,
            chat_id=chat_id,
            telegram_user=telegram_user,
        )

        # Получаем auth_id из созданной записи
        auth_repo = AuthRepository()
        auth_account = await auth_repo.get_by_identifier(
            db_session, f"tg_{telegram_user.telegram_id}"
        )
        assert auth_account is not None

        category = await CategoryRepository().create(
            db_session,
            {
                "name": "Backend",
                "slug": "backend",
                "description": "Backend vacancies",
                "is_active": True,
            },
        )

        # Act — запрашиваем список категорий
        mock_bus.published.clear()
        await subscription_service.handle_subscribe(
            session=db_session,
            chat_id=chat_id,
            telegram_id=telegram_user.telegram_id,
        )

        # Подписка ещё не создаётся до выбора кнопки
        repo = SubscriptionRepository()
        sub = await repo.get_by_auth_id(session=db_session, auth_id=auth_account.id)
        assert sub is None
        payload = mock_bus.published[-1][1]
        assert payload["text"] == (
            "Выберите категорию вакансий для подписки:\n\nСтраница 1 из 1"
        )
        assert payload["keyboard"]["inline_keyboard"][0][0] == {
            "text": "Backend",
            "callback_data": f"subscribe_category:{category.id}",
        }
        assert payload["keyboard"]["inline_keyboard"][-1] == [
            {"text": "← Назад", "callback_data": "subscribe_page:noop"},
            {"text": "Вперёд →", "callback_data": "subscribe_page:noop"},
        ]

        # Act — пользователь выбирает категорию
        mock_bus.published.clear()
        await subscription_service.handle_category_subscription(
            session=db_session,
            chat_id=chat_id,
            telegram_id=telegram_user.telegram_id,
            message_id=101,
            category_id=category.id,
        )

        sub = await repo.get_by_auth_id(session=db_session, auth_id=auth_account.id)
        assert sub is not None
        assert sub.auth_id == auth_account.id
        assert sub.is_active is True
        assert sub.category_ids == [str(category.id)]
        assert mock_bus.published[-1][0] == BusTopics.BOT_MESSAGE_EDIT
        assert mock_bus.published[-1][1]["message_id"] == 101
        assert mock_bus.published[-1][1]["keyboard"] is None
        assert "Backend" in mock_bus.published[-1][1]["text"]

        # Повторный callback идемпотентен и не дублирует категорию
        await subscription_service.handle_category_subscription(
            session=db_session,
            chat_id=chat_id,
            telegram_id=telegram_user.telegram_id,
            message_id=101,
            category_id=category.id,
        )
        sub = await repo.get_by_auth_id(session=db_session, auth_id=auth_account.id)
        assert sub is not None
        assert sub.category_ids == [str(category.id)]

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
        await auth_repo.create(
            db_session,
            {
                "identifier": "tg_777777",
                "identifier_type": "telegram",
                "hashed_password": "hashed",
            },
        )

        mock_bus = MockBus()
        service = JobMatcherUserService(
            subscription_repository=SubscriptionRepository(),
            bus=mock_bus,
        )

        # Act — повторный вызов
        await service.handle_start(
            session=db_session,
            chat_id=777777,
            telegram_user=TelegramUserInfo(
                telegram_id=777777,
                username="existing",
                first_name="Existing",
            ),
        )

        # Assert — сообщение о том, что уже зарегистрирован
        assert len(mock_bus.published) > 0
        assert "уже зарегистрированы" in mock_bus.published[0][1]["text"]
