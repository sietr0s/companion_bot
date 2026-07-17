"""
Тесты шины сообщений: InMemoryProducer, BaseEvent, InMemoryConsumer.
"""

import uuid

from src.bus.in_memory.consumer import InMemoryConsumer
from src.bus.in_memory.producer import InMemoryProducer
from src.modules.auth.schemas.events import UserLoggedIn, UserRegistered
from src.modules.users.schemas.events import ProfileCreated, ProfileDeleted, ProfileUpdated


class TestBaseEvent:
    """Тесты базового класса событий."""

    def test_user_registered_to_bus_dict(self):
        """UserRegistered корректно сериализуется через to_bus_dict."""
        auth_id = uuid.uuid4()
        event = UserRegistered(
            auth_id=auth_id,
            identifier="test@test.com",
            identifier_type="email",
        )
        data = event.to_bus_dict()

        assert data["event_name"] == "auth.event.user.registered"
        assert data["auth_id"] == str(auth_id)
        assert data["identifier"] == "test@test.com"
        assert data["identifier_type"] == "email"
        assert "timestamp" in data

    def test_user_logged_in_to_bus_dict(self):
        event = UserLoggedIn(
            auth_id=uuid.uuid4(),
            identifier="a@b.com",
            identifier_type="email",
        )
        data = event.to_bus_dict()
        assert data["event_name"] == "auth.event.user.logged_in"

    def test_profile_updated_to_bus_dict(self):
        event = ProfileUpdated(
            auth_id=uuid.uuid4(),
            profile_id=uuid.uuid4(),
            fields_updated=["first_name", "bio"],
        )
        data = event.to_bus_dict()
        assert data["event_name"] == "users.event.profile.updated"
        assert data["fields_updated"] == ["first_name", "bio"]

    def test_profile_created_to_bus_dict(self):
        event = ProfileCreated(
            auth_id=uuid.uuid4(),
            profile_id=uuid.uuid4(),
        )
        data = event.to_bus_dict()
        assert data["event_name"] == "users.event.profile.created"
        assert "auth_id" in data
        assert "profile_id" in data

    def test_profile_deleted_to_bus_dict(self):
        event = ProfileDeleted(
            auth_id=uuid.uuid4(),
            profile_id=uuid.uuid4(),
        )
        data = event.to_bus_dict()
        assert data["event_name"] == "users.event.profile.deleted"
        assert "auth_id" in data
        assert "profile_id" in data


class TestInMemoryProducer:
    """Тесты in-memory продюсера."""

    async def test_subscribe_and_publish(self):
        """Обработчик вызывается при публикации в топик."""
        bus = InMemoryProducer()
        received = []

        @bus.subscribe("test.topic")
        async def handler(message):
            received.append(message)

        await bus.publish("test.topic", {"key": "value"})
        # Даём event loop время выполнить create_task
        import asyncio

        await asyncio.sleep(0.05)
        assert len(received) == 1
        assert received[0]["key"] == "value"

    def test_multiple_subscribers(self):
        """Несколько обработчиков на один топик."""
        bus = InMemoryProducer()

        @bus.subscribe("multi")
        async def handler1(msg):
            pass

        @bus.subscribe("multi")
        async def handler2(msg):
            pass

        assert len(bus.get_subscribers()["multi"]) == 2

    async def test_publish_no_subscribers(self):
        """Публикация в топик без подписчиков не вызывает ошибку."""
        bus = InMemoryProducer()
        await bus.publish("empty.topic", {"data": "test"})

    async def test_async_handler_called(self):
        """Асинхронный обработчик получает сообщение."""
        bus = InMemoryProducer()
        received = []

        @bus.subscribe("async.topic")
        async def handler(message):
            received.append(message)

        await bus.publish("async.topic", {"payload": 42})
        # Даём event loop время выполнить create_task
        import asyncio

        await asyncio.sleep(0.05)
        assert len(received) == 1
        assert received[0]["payload"] == 42

    async def test_start_stop(self):
        """start/stop не вызывают ошибок (заглушки)."""
        bus = InMemoryProducer()
        await bus.start()
        await bus.stop()


class TestInMemoryConsumer:
    """Тесты in-memory консьюмера."""

    async def test_start_stop(self):
        """start/stop не вызывают ошибок (заглушки)."""
        consumer = InMemoryConsumer(subscribers={})
        await consumer.start()
        await consumer.stop()
