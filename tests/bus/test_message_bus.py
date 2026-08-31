"""
Тесты шины сообщений: InMemoryProducer, BaseEvent, InMemoryConsumer.
"""

import uuid

from src.bus.in_memory.consumer import InMemoryConsumer
from src.bus.in_memory.producer import InMemoryProducer
from src.bus.in_memory.transport import InMemoryTransport
from src.modules.auth.schemas.events import UserLoggedIn, UserRegistered
from src.modules.users.schemas.events import UserCreated, UserUpdated


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

    def test_user_created_to_bus_dict(self):
        user_id = uuid.uuid4()
        event = UserCreated(user_id=user_id, telegram_id=42)
        data = event.to_bus_dict()
        assert data["event_name"] == "users.event.created"
        assert data["user_id"] == str(user_id)
        assert data["telegram_id"] == 42

    def test_user_updated_to_bus_dict(self):
        event = UserUpdated(
            user_id=uuid.uuid4(),
            telegram_id=42,
            fields_updated=["first_name", "notes"],
        )
        data = event.to_bus_dict()
        assert data["event_name"] == "users.event.updated"
        assert data["fields_updated"] == ["first_name", "notes"]


class TestInMemoryProducer:
    """Тесты in-memory продюсера."""

    async def test_subscribe_and_publish(self):
        """Обработчик вызывается при публикации в топик."""
        transport = InMemoryTransport()
        producer = InMemoryProducer(transport)
        consumer = InMemoryConsumer(transport, producer)
        received = []

        @consumer.subscribe("test.topic")
        async def handler(message):
            received.append(message)

        await consumer.start()
        await producer.publish("test.topic", {"key": "value"})
        await transport.queue.join()
        await consumer.stop()
        assert len(received) == 1
        assert received[0]["key"] == "value"

    def test_multiple_subscribers(self):
        """Несколько обработчиков на один топик."""
        transport = InMemoryTransport()
        producer = InMemoryProducer(transport)
        consumer = InMemoryConsumer(transport, producer)

        @consumer.subscribe("multi")
        async def handler1(msg):
            pass

        @consumer.subscribe("multi")
        async def handler2(msg):
            pass

        assert len(consumer.get_subscribers()["multi"]) == 2

    async def test_publish_no_subscribers(self):
        """Публикация в топик без подписчиков не вызывает ошибку."""
        bus = InMemoryProducer()
        await bus.publish("empty.topic", {"data": "test"})

    async def test_async_handler_called(self):
        """Асинхронный обработчик получает сообщение."""
        transport = InMemoryTransport()
        producer = InMemoryProducer(transport)
        consumer = InMemoryConsumer(transport, producer)
        received = []

        @consumer.subscribe("async.topic")
        async def handler(message):
            received.append(message)

        await consumer.start()
        await producer.publish("async.topic", {"payload": 42})
        await transport.queue.join()
        await consumer.stop()
        assert len(received) == 1
        assert received[0]["payload"] == 42

    async def test_start_stop(self):
        """Producer не требует отдельной фоновой задачи."""
        bus = InMemoryProducer()
        await bus.start()
        await bus.stop()


class TestInMemoryConsumer:
    """Тесты in-memory консьюмера."""

    async def test_start_stop(self):
        """Consumer запускает и корректно останавливает чтение очереди."""
        transport = InMemoryTransport()
        producer = InMemoryProducer(transport)
        consumer = InMemoryConsumer(transport, producer)
        await consumer.start()
        await consumer.stop()
