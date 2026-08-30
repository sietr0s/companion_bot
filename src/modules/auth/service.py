"""
Сервис авторизации.

Содержит бизнес-логику регистрации и входа.
Модуль auth полностью изолирован — он не создаёт профиль
пользователя и не зависит от модуля users.
Профиль создаётся отдельным запросом через роут /users/.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.service import BaseService
from src.bus.interface import MessageProducer
from src.core.bus_topics import BusTopics
from src.core.exceptions import ConflictError, UnauthorizedError
from src.core.security import create_access_token, hash_password, verify_password
from src.modules.auth.constants import ERROR_MESSAGES
from src.modules.auth.models import Auth
from src.modules.auth.repository import AuthRepository
from src.modules.auth.schemas.internal import AuthRead, VerifyTokenResponse
from src.modules.auth.schemas_api import TokenResponse, AccountResponse
from src.modules.auth.schemas_bus import UserDeleted, UserLoggedIn, UserRegistered


class AuthService(BaseService[AuthRepository, Auth]):
    """
    Сервис авторизации: регистрация и вход.

    При регистрации:
    1. Проверяет уникальность email
    2. Хэширует пароль
    3. Создаёт AuthAccount
    4. Публикует событие UserRegistered

    При входе:
    1. Ищет учётную запись по email
    2. Проверяет пароль
    3. Генерирует JWT-токен
    4. Публикует событие UserLoggedIn
    """

    def __init__(self, repository: AuthRepository, message_bus: MessageProducer) -> None:
        super().__init__(repository)
        self.message_bus = message_bus

    async def register(
        self,
        session: AsyncSession,
        data: dict,
    ) -> TokenResponse:
        """
        Регистрация нового пользователя.

        Создаёт только учётную запись авторизации.
        Профиль пользователя создаётся отдельным запросом
        через POST /users/ с auth_id из JWT.

        Поддерживает опциональное поле role в data — если не указано,
        используется значение по умолчанию из модели Auth ("user").
        """
        # Проверяем уникальность identifier
        existing = await self.repository.get_by_identifier(session, data["identifier"])
        if existing:
            raise ConflictError(
                detail=ERROR_MESSAGES["duplicate_identifier"].format(
                    identifier_type=data["identifier_type"]
                )
            )

        # Хэшируем пароль и создаём учётную запись
        hashed_pw = hash_password(data["password"])
        account_data = {
            "identifier": data["identifier"],
            "identifier_type": data["identifier_type"],
            "hashed_password": hashed_pw,
        }
        # Пробрасываем role, если указана (для seed admin)
        if "role" in data:
            account_data["role"] = data["role"]
        account = await self.repository.create(session, account_data)

        # Публикуем событие о регистрации
        event = UserRegistered(
            auth_id=account.id,
            identifier=account.identifier,
            identifier_type=account.identifier_type,
        )
        await self.message_bus.publish(BusTopics.USER_REGISTERED, event.to_bus_dict())

        # Генерируем токен для автоматического входа после регистрации
        token = create_access_token(str(account.id), account.role)
        return TokenResponse(access_token=token)

    async def register_and_return_id(
        self,
        session: AsyncSession,
        data: dict,
    ) -> uuid.UUID:
        """
        Регистрация нового пользователя и возврат его ID.

        Для использования из клиентов других модулей.
        Не публикует событие — только создаёт учётную запись.
        """
        existing = await self.repository.get_by_identifier(session, data["identifier"])
        if existing:
            raise ConflictError(
                detail=ERROR_MESSAGES["duplicate_identifier"].format(
                    identifier_type=data["identifier_type"]
                )
            )

        hashed_pw = hash_password(data["password"])
        account = await self.repository.create(
            session,
            {
                "identifier": data["identifier"],
                "identifier_type": data["identifier_type"],
                "hashed_password": hashed_pw,
            },
        )

        return account.id

    async def login(
        self,
        session: AsyncSession,
        data: dict,
    ) -> TokenResponse:
        """Авторизация пользователя: проверяет identifier/пароль и возвращает JWT."""
        account = await self.repository.get_by_identifier(session, data["identifier"])
        if not account:
            raise UnauthorizedError(detail=ERROR_MESSAGES["invalid_credentials"])

        if not verify_password(data["password"], account.hashed_password):
            raise UnauthorizedError(detail=ERROR_MESSAGES["invalid_credentials"])

        # Публикуем событие о входе
        event = UserLoggedIn(
            auth_id=account.id,
            identifier=account.identifier,
            identifier_type=account.identifier_type,
        )
        await self.message_bus.publish(BusTopics.USER_LOGGED_IN, event.to_bus_dict())

        token = create_access_token(str(account.id), account.role)
        return TokenResponse(access_token=token)

    async def change_password(
        self,
        session: AsyncSession,
        auth_id: uuid.UUID,
        current_password: str,
        new_password: str,
    ) -> None:
        """Сменить пароль пользователя."""
        account = await self.repository.get_by_id(session, auth_id)
        if not account:
            raise UnauthorizedError(detail="Учётная запись не найдена")

        if not verify_password(current_password, account.hashed_password):
            raise UnauthorizedError(detail="Неверный текущий пароль")

        hashed_pw = hash_password(new_password)
        await self.repository.update(session, account, {"hashed_password": hashed_pw})

    async def delete_account(
        self,
        session: AsyncSession,
        auth_id: uuid.UUID,
    ) -> None:
        """Удалить учётную запись (без пароля — по JWT)."""
        account = await self.repository.get_by_id(session, auth_id)
        if not account:
            raise UnauthorizedError(detail="Учётная запись не найдена")

        await self.repository.delete(session, account)

        # Публикуем событие в шину
        event = UserDeleted(auth_id=auth_id)
        await self.message_bus.publish(BusTopics.USER_DELETED, event.to_bus_dict())

    async def list_accounts(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        order_by: str | None = "-created_at",
    ) -> tuple[list[AccountResponse], int]:
        """Получить список всех аккаунтов с пагинацией."""
        accounts, total = await self.repository.get_list(
            session, skip=skip, limit=limit, order_by=order_by
        )
        return [AccountResponse.model_validate(acc) for acc in accounts], total

    async def get_account(
        self,
        session: AsyncSession,
        account_id: uuid.UUID,
    ) -> AccountResponse:
        """Получить аккаунт по ID."""
        account = await self.repository.get_by_id(session, account_id)
        if not account:
            raise UnauthorizedError(detail="Учётная запись не найдена")
        return AccountResponse.model_validate(account)

    async def create_account(
        self,
        session: AsyncSession,
        data: dict,
    ) -> AuthRead:
        """Создать учётную запись (internal)."""
        # Проверяем уникальность identifier
        existing = await self.repository.get_by_identifier(session, data["identifier"])
        if existing:
            raise ConflictError(
                detail=ERROR_MESSAGES["duplicate_identifier"].format(
                    identifier_type=data["identifier_type"]
                )
            )

        account = await self.repository.create(session, data)
        return account

    async def update_account(
        self,
        session: AsyncSession,
        auth_id: uuid.UUID,
        data: dict,
    ) -> AuthRead:
        """Обновить учётную запись (internal)."""
        account = await self.get_by_id(session, auth_id)
        if not account:
            raise UnauthorizedError(detail="Учётная запись не найдена")

        updated = await self.repository.update(session, account, data)
        return updated

    async def delete_account_internal(
        self,
        session: AsyncSession,
        auth_id: uuid.UUID,
    ) -> None:
        """Удалить учётную запись без проверки пароля (internal)."""
        account = await self.get_by_id(session, auth_id)
        if not account:
            raise UnauthorizedError(detail="Учётная запись не найдена")
        await self.repository.delete(session, account)

    async def verify_token_internal(
        self,
        token: str,
    ) -> VerifyTokenResponse:
        """Проверить валидность токена (internal)."""
        from jwt import ExpiredSignatureError, InvalidTokenError

        from src.core.security import decode_access_token

        try:
            payload = decode_access_token(token)
            auth_id = payload.get("sub")
            role = payload.get("role")

            return VerifyTokenResponse(
                valid=True,
                auth_id=uuid.UUID(auth_id) if auth_id else None,
                role=role,
            )
        except ExpiredSignatureError:
            # Токен истёк
            return VerifyTokenResponse(valid=False)
        except InvalidTokenError:
            # Невалидный токен
            return VerifyTokenResponse(valid=False)
        except (ValueError, AttributeError):
            # Ошибка парсинга payload
            return VerifyTokenResponse(valid=False)
