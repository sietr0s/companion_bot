"""
Тесты базового сервиса.

Проверяем, что сервис корректно проксирует вызовы к репозиторию.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.service import AuthService


class TestBaseService:
    """Тесты проксирующих методов BaseService через AuthService."""

    async def test_get_by_id(self, db_session: AsyncSession, auth_service: AuthService):
        """Сервис проксирует get_by_id к репозиторию."""
        account = await auth_service.create(
            db_session,
            {
                "identifier": "svc@test.com",
                "identifier_type": "email",
                "hashed_password": "hashed",
            },
        )
        found = await auth_service.get_by_id(db_session, account.id)
        assert found is not None
        assert found.identifier == "svc@test.com"

    async def test_get_all(self, db_session: AsyncSession, auth_service: AuthService):
        """Сервис проксирует get_all к репозиторию."""
        await auth_service.create(
            db_session,
            {
                "identifier": "svc1@test.com",
                "identifier_type": "email",
                "hashed_password": "hashed",
            },
        )
        results = await auth_service.get_all(db_session)
        assert len(results) >= 1

    async def test_create(self, db_session: AsyncSession, auth_service: AuthService):
        """Сервис проксирует create к репозиторию."""
        account = await auth_service.create(
            db_session,
            {
                "identifier": "svc_create@test.com",
                "identifier_type": "email",
                "hashed_password": "hashed",
            },
        )
        assert account.identifier == "svc_create@test.com"

    async def test_update(self, db_session: AsyncSession, auth_service: AuthService):
        """Сервис проксирует update к репозиторию."""
        account = await auth_service.create(
            db_session,
            {
                "identifier": "svc_upd@test.com",
                "identifier_type": "email",
                "hashed_password": "old",
            },
        )
        updated = await auth_service.update(
            db_session,
            account.id,
            {
                "hashed_password": "new",
            },
        )
        assert updated.hashed_password == "new"

    async def test_delete(self, db_session: AsyncSession, auth_service: AuthService):
        """Сервис проксирует delete к репозиторию."""
        account = await auth_service.create(
            db_session,
            {
                "identifier": "svc_del@test.com",
                "identifier_type": "email",
                "hashed_password": "hashed",
            },
        )
        await auth_service.delete(db_session, account.id)
        found = await auth_service.get_by_id(db_session, account.id)
        assert found is None
