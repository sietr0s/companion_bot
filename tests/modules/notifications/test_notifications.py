"""Тесты модуля нотификаций."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.bus_topics import BusTopics
from src.modules.notifications.repository import (
    NotificationLogRepository,
    NotificationTemplateRepository,
)
from src.modules.notifications.schemas.events import NotificationSend
from src.modules.notifications.schemas.public import TemplateCreate, TemplateUpdate
from src.modules.notifications.service import NotificationService
from src.modules.notifications.template_engine import render


class TestNotificationTemplateRepository:
    """Тесты репозитория шаблонов."""

    @pytest_asyncio.fixture
    def repo(self):
        return NotificationTemplateRepository()

    @pytest.mark.asyncio
    async def test_create_template(self, db_session: AsyncSession, repo):
        template = await repo.create(
            db_session,
            {
                "name": "welcome",
                "channel": "email",
                "subject_template": "Hello {{ name }}",
                "body_template": "<h1>Welcome {{ name }}</h1>",
            },
        )
        assert template.name == "welcome"
        assert template.channel == "email"
        assert template.is_active is True

    @pytest.mark.asyncio
    async def test_get_by_name(self, db_session: AsyncSession, repo):
        await repo.create(
            db_session,
            {
                "name": "reset",
                "channel": "email",
                "body_template": "Reset link: {{ link }}",
            },
        )
        found = await repo.get_by_name(db_session, "reset", "email")
        assert found is not None
        assert found.name == "reset"

    @pytest.mark.asyncio
    async def test_get_by_name_not_found(self, db_session: AsyncSession, repo):
        found = await repo.get_by_name(db_session, "nonexistent", "email")
        assert found is None

    @pytest.mark.asyncio
    async def test_get_by_name_inactive_skipped(self, db_session: AsyncSession, repo):
        await repo.create(
            db_session,
            {
                "name": "inactive_tpl",
                "channel": "email",
                "body_template": "Inactive",
                "is_active": False,
            },
        )
        found = await repo.get_by_name(db_session, "inactive_tpl", "email")
        assert found is None


class TestNotificationLogRepository:
    """Тесты репозитория логов."""

    @pytest_asyncio.fixture
    def repo(self):
        return NotificationLogRepository()

    @pytest.mark.asyncio
    async def test_create_log(self, db_session: AsyncSession, repo):
        auth_id = uuid.uuid4()
        log = await repo.create(
            db_session,
            {
                "auth_id": auth_id,
                "channel": "email",
                "template_name": "welcome",
                "recipient": "test@test.com",
                "subject": "Welcome",
                "body": "<h1>Welcome</h1>",
                "status": "sent",
            },
        )
        assert log.status == "sent"
        assert log.recipient == "test@test.com"

    @pytest.mark.asyncio
    async def test_get_by_auth_id(self, db_session: AsyncSession, repo):
        auth_id = uuid.uuid4()
        await repo.create(
            db_session,
            {
                "auth_id": auth_id,
                "channel": "email",
                "template_name": "welcome",
                "recipient": "test@test.com",
                "body": "Hello",
                "status": "sent",
            },
        )
        logs = await repo.get_by_auth_id(db_session, auth_id)
        assert len(logs) == 1
        assert logs[0].auth_id == auth_id


class TestNotificationSendEvent:
    """Тесты события NotificationSend."""

    def test_event_fields(self):
        auth_id = uuid.uuid4()
        event = NotificationSend(
            auth_id=auth_id,
            template_name="welcome",
            channel="email",
            body={"first_name": "Ivan"},
        )
        assert event.event_name == BusTopics.NOTIFICATION_SEND
        assert event.auth_id == auth_id
        assert event.template_name == "welcome"
        assert event.body == {"first_name": "Ivan"}

    def test_to_bus_dict(self):
        event = NotificationSend(
            auth_id=uuid.uuid4(),
            template_name="reset",
            body={"link": "https://..."},
        )
        d = event.to_bus_dict()
        assert d["event_name"] == BusTopics.NOTIFICATION_SEND
        assert "auth_id" in d
        assert d["template_name"] == "reset"


class TestTemplateEngine:
    """Тесты Jinja2-рендеринга."""

    def test_render_simple(self):
        result = render("Hello {{ name }}!", {"name": "Ivan"})
        assert result == "Hello Ivan!"

    def test_render_html(self):
        result = render("<h1>{{ title }}</h1>", {"title": "Welcome"})
        assert result == "<h1>Welcome</h1>"

    def test_render_conditional(self):
        result = render(
            "{% if active %}Active{% else %}Inactive{% endif %}",
            {"active": True},
        )
        assert result == "Active"


class TestNotificationService:
    """Тесты сервиса нотификаций."""

    @pytest_asyncio.fixture
    def service(self):

        class MockProvider:
            async def send(self, to, subject, body):
                pass

            async def start(self):
                pass

            async def stop(self):
                pass

        return NotificationService(
            template_repo=NotificationTemplateRepository(),
            log_repo=NotificationLogRepository(),
            provider=MockProvider(),
        )

    @pytest.mark.asyncio
    async def test_create_template(self, db_session: AsyncSession, service):
        data = TemplateCreate(
            name="test_tpl",
            channel="email",
            body_template="Hello {{ name }}",
        )
        template = await service.create_template(db_session, data)
        assert template.name == "test_tpl"

    @pytest.mark.asyncio
    async def test_get_template(self, db_session: AsyncSession, service):
        data = TemplateCreate(
            name="fetch_tpl",
            channel="email",
            body_template="Body",
        )
        created = await service.create_template(db_session, data)
        found = await service.get_template(db_session, created.id)
        assert found.name == "fetch_tpl"

    @pytest.mark.asyncio
    async def test_update_template(self, db_session: AsyncSession, service):
        data = TemplateCreate(
            name="upd_tpl",
            channel="email",
            body_template="Old body",
        )
        created = await service.create_template(db_session, data)
        updated = await service.update_template(
            db_session, created.id, TemplateUpdate(body_template="New body")
        )
        assert updated.body_template == "New body"

    @pytest.mark.asyncio
    async def test_delete_template(self, db_session: AsyncSession, service):
        data = TemplateCreate(
            name="del_tpl",
            channel="email",
            body_template="Bye",
        )
        created = await service.create_template(db_session, data)
        await service.delete_template(db_session, created.id)
        from src.core.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            await service.get_template(db_session, created.id)

    @pytest.mark.asyncio
    async def test_send_notification_with_db_template(
        self,
        db_session: AsyncSession,
        service,
        mock_users_client,
    ):
        # Создаём шаблон в БД
        await service.create_template(
            db_session,
            TemplateCreate(
                name="greet",
                channel="email",
                subject_template="Hi {{ name }}",
                body_template="Hello {{ name }}!",
            ),
        )

        auth_id = uuid.uuid4()
        log = await service.send_notification(
            session=db_session,
            auth_id=auth_id,
            template_name="greet",
            channel="email",
            body={"name": "Ivan"},
        )
        assert log.status == "sent"
        assert log.subject == "Hi Ivan"
        assert log.body == "Hello Ivan!"
        assert "user" in log.recipient
        assert "@test.com" in log.recipient

    @pytest.mark.asyncio
    async def test_send_notification_no_template(
        self,
        db_session: AsyncSession,
        service,
        mock_users_client,
    ):
        auth_id = uuid.uuid4()
        log = await service.send_notification(
            session=db_session,
            auth_id=auth_id,
            template_name="nonexistent",
            channel="email",
            body={"key": "value"},
        )
        assert log.status == "sent"
        # Без шаблона body превращается в строку
        assert log.body is not None

    @pytest.mark.asyncio
    async def test_get_history(self, db_session: AsyncSession, service, mock_users_client):
        auth_id = uuid.uuid4()
        await service.send_notification(
            session=db_session,
            auth_id=auth_id,
            template_name="test",
            channel="email",
            body={},
        )
        history = await service.get_history(db_session, skip=0, limit=10)
        assert len(history) >= 1
