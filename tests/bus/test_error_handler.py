"""
Тесты обработчика ошибок шины сообщений.

Проверяет:
- Обработка бизнес-исключений (AppException) без падения
- Обработка сетевых и неожиданных ошибок без падения
- Проброс CancelledError
- Успешный вызов обработчика
- wrap_handler — обёртка обработчика
"""

import asyncio

import pytest

from src.bus.error_handler import safe_handle, wrap_handler
from src.core.exceptions import ConflictError, NotFoundError


class TestSafeHandle:
    """Тесты safe_handle — безопасного вызова обработчика."""

    async def test_successful_handler(self):
        """Успешный вызов обработчика — без ошибок."""
        received = []

        async def handler(message: dict) -> None:
            received.append(message)

        await safe_handle(handler, "test.topic", {"key": "value"})

        assert len(received) == 1
        assert received[0]["key"] == "value"

    async def test_sync_handler(self):
        """Синхронный обработчик тоже работает."""
        received = []

        def handler(message: dict) -> None:
            received.append(message)

        await safe_handle(handler, "test.topic", {"key": "value"})

        assert len(received) == 1

    async def test_app_exception_is_swallowed(self):
        """Бизнес-исключение (NotFoundError) логируется и не пробрасывается."""

        async def handler(message: dict) -> None:
            raise NotFoundError(detail="Ресурс не найден")

        await safe_handle(handler, "test.topic", {"id": 42})

    async def test_conflict_error_is_swallowed(self):
        """ConflictError логируется и не пробрасывается."""

        async def handler(message: dict) -> None:
            raise ConflictError(detail="Дубликат")

        await safe_handle(handler, "test.topic", {})

    async def test_connection_error_is_swallowed(self):
        """ConnectionError логируется и не пробрасывается."""

        async def handler(message: dict) -> None:
            raise ConnectionError("Connection refused")

        await safe_handle(handler, "test.topic", {})

    async def test_timeout_error_is_swallowed(self):
        """TimeoutError логируется и не пробрасывается."""

        async def handler(message: dict) -> None:
            raise TimeoutError("Timed out")

        await safe_handle(handler, "test.topic", {})

    async def test_unexpected_error_is_swallowed(self):
        """Неожиданная ошибка (ValueError) логируется и не пробрасывается."""

        async def handler(message: dict) -> None:
            raise ValueError("Invalid value")

        await safe_handle(handler, "test.topic", {})

    async def test_cancelled_error_propagates(self):
        """CancelledError пробрасывается наверх."""

        async def handler(message: dict) -> None:
            raise asyncio.CancelledError()

        with pytest.raises(asyncio.CancelledError):
            await safe_handle(handler, "test.topic", {})

    async def test_handler_without_name(self):
        """Обработчик без __name__ (lambda) не вызывает ошибку."""

        async def handler(message: dict) -> None:
            raise ValueError("Error")

        handler.__name__ = ""

        await safe_handle(handler, "test.topic", {})


class TestWrapHandler:
    """Тесты wrap_handler — обёртки обработчика."""

    async def test_wrap_handler_success(self):
        """Обёрнутый обработчик успешно вызывается."""
        received = []

        async def handler(message: dict) -> None:
            received.append(message)

        wrapped = wrap_handler(handler, "test.topic")
        await wrapped({"key": "value"})

        assert len(received) == 1
        assert received[0]["key"] == "value"

    async def test_wrap_handler_preserves_metadata(self):
        """Обёртка сохраняет __name__, __module__, __doc__."""

        async def my_handler(message: dict) -> None:
            """My docstring."""
            pass

        wrapped = wrap_handler(my_handler, "test.topic")

        assert wrapped.__name__ == "my_handler"
        assert wrapped.__module__ == my_handler.__module__
        assert wrapped.__doc__ == "My docstring."

    async def test_wrap_handler_app_exception_is_swallowed(self):
        """Обёрнутый обработчик глотает бизнес-ошибки."""

        async def handler(message: dict) -> None:
            raise NotFoundError(detail="Not found")

        wrapped = wrap_handler(handler, "test.topic")
        await wrapped({})


class TestInMemoryConsumerWithErrors:
    """Тесты обработки ошибок в InMemoryConsumer."""

    async def test_handler_error_does_not_crash_producer(self):
        """Ошибка в одном обработчике не влияет на другие."""
        from src.bus.in_memory.consumer import InMemoryConsumer
        from src.bus.in_memory.producer import InMemoryProducer
        from src.bus.in_memory.transport import InMemoryTransport

        transport = InMemoryTransport()
        producer = InMemoryProducer(transport)
        consumer = InMemoryConsumer(transport)
        received = []

        @consumer.subscribe("test.topic")
        async def failing_handler(message: dict) -> None:
            raise ValueError("Ошибка")

        @consumer.subscribe("test.topic")
        async def success_handler(message: dict) -> None:
            received.append(message)

        await consumer.start()
        await producer.publish("test.topic", {"key": "value"})
        await transport.queue.join()
        await consumer.stop()

        assert len(received) == 1

    async def test_app_exception_in_handler_does_not_crash_producer(self):
        """AppException в обработчике не крашит продюсер."""
        from src.bus.in_memory.consumer import InMemoryConsumer
        from src.bus.in_memory.producer import InMemoryProducer
        from src.bus.in_memory.transport import InMemoryTransport

        transport = InMemoryTransport()
        producer = InMemoryProducer(transport)
        consumer = InMemoryConsumer(transport)

        @consumer.subscribe("test.topic")
        async def handler(message: dict) -> None:
            raise NotFoundError(detail="Not found")

        await consumer.start()
        await producer.publish("test.topic", {"id": 1})
        await transport.queue.join()
        await consumer.stop()
