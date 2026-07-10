"""
Тесты BusErrorHandler — единого обработчика ошибок для шины сообщений.

Проверяет:
- Обработка бизнес-исключений (AppException) → публикация в DLQ
- Обработка сетевых ошибок (ConnectionError, TimeoutError) → публикация в DLQ
- Обработка неожиданных ошибок → публикация в DLQ
- Проброс CancelledError
- Успешный вызов обработчика без ошибок
- wrap_handler — обёртка обработчика
"""

import asyncio

import pytest

from src.bus.error_handler import DLQ_TOPIC, safe_handle, wrap_handler
from src.core.exceptions import ConflictError, NotFoundError


class TestSafeHandle:
    """Тесты safe_handle — безопасного вызова обработчика."""

    async def test_successful_handler(self):
        """Успешный вызов обработчика — без ошибок, без DLQ."""
        received = []

        async def handler(message: dict) -> None:
            received.append(message)

        dlq_calls = []

        async def dlq_publisher(topic: str, message: dict) -> None:
            dlq_calls.append((topic, message))

        await safe_handle(handler, "test.topic", {"key": "value"}, dlq_publisher)

        assert len(received) == 1
        assert received[0]["key"] == "value"
        assert len(dlq_calls) == 0

    async def test_sync_handler(self):
        """Синхронный обработчик тоже работает."""
        received = []

        def handler(message: dict) -> None:
            received.append(message)

        await safe_handle(handler, "test.topic", {"key": "value"})

        assert len(received) == 1

    async def test_app_exception_publishes_to_dlq(self):
        """Бизнес-исключение (NotFoundError) → публикация в DLQ."""

        async def handler(message: dict) -> None:
            raise NotFoundError(detail="Ресурс не найден")

        dlq_calls = []

        async def dlq_publisher(topic: str, message: dict) -> None:
            dlq_calls.append((topic, message))

        await safe_handle(handler, "test.topic", {"id": 42}, dlq_publisher)

        assert len(dlq_calls) == 1
        topic, msg = dlq_calls[0]
        assert topic == DLQ_TOPIC
        assert msg["original_topic"] == "test.topic"
        assert msg["error_type"] == "NotFoundError"
        assert msg["error_detail"] == "Ресурс не найден"
        assert msg["handler"] == "handler"
        assert msg["message"] == {"id": 42}

    async def test_conflict_error_publishes_to_dlq(self):
        """ConflictError → публикация в DLQ."""

        async def handler(message: dict) -> None:
            raise ConflictError(detail="Дубликат")

        dlq_calls = []

        async def dlq_publisher(topic: str, message: dict) -> None:
            dlq_calls.append((topic, message))

        await safe_handle(handler, "test.topic", {}, dlq_publisher)

        assert len(dlq_calls) == 1
        assert dlq_calls[0][1]["error_type"] == "ConflictError"

    async def test_connection_error_publishes_to_dlq(self):
        """ConnectionError → публикация в DLQ."""

        async def handler(message: dict) -> None:
            raise ConnectionError("Connection refused")

        dlq_calls = []

        async def dlq_publisher(topic: str, message: dict) -> None:
            dlq_calls.append((topic, message))

        await safe_handle(handler, "test.topic", {}, dlq_publisher)

        assert len(dlq_calls) == 1
        assert dlq_calls[0][1]["error_type"] == "ConnectionError"

    async def test_timeout_error_publishes_to_dlq(self):
        """TimeoutError → публикация в DLQ."""

        async def handler(message: dict) -> None:
            raise TimeoutError("Timed out")

        dlq_calls = []

        async def dlq_publisher(topic: str, message: dict) -> None:
            dlq_calls.append((topic, message))

        await safe_handle(handler, "test.topic", {}, dlq_publisher)

        assert len(dlq_calls) == 1
        assert dlq_calls[0][1]["error_type"] == "TimeoutError"

    async def test_unexpected_error_publishes_to_dlq(self):
        """Неожиданная ошибка (ValueError) → публикация в DLQ."""

        async def handler(message: dict) -> None:
            raise ValueError("Invalid value")

        dlq_calls = []

        async def dlq_publisher(topic: str, message: dict) -> None:
            dlq_calls.append((topic, message))

        await safe_handle(handler, "test.topic", {}, dlq_publisher)

        assert len(dlq_calls) == 1
        assert dlq_calls[0][1]["error_type"] == "ValueError"
        # Для неожиданных ошибок должен быть traceback
        assert "traceback" in dlq_calls[0][1]

    async def test_cancelled_error_propagates(self):
        """CancelledError пробрасывается наверх — не попадает в DLQ."""

        async def handler(message: dict) -> None:
            raise asyncio.CancelledError()

        dlq_calls = []

        async def dlq_publisher(topic: str, message: dict) -> None:
            dlq_calls.append((topic, message))

        with pytest.raises(asyncio.CancelledError):
            await safe_handle(handler, "test.topic", {}, dlq_publisher)

        assert len(dlq_calls) == 0

    async def test_no_dlq_publisher_no_crash(self):
        """Без dlq_publisher ошибка логируется, но не падает."""

        async def handler(message: dict) -> None:
            raise NotFoundError(detail="Not found")

        # Не должно быть исключения
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

    async def test_wrap_handler_app_exception_to_dlq(self):
        """Обёрнутый обработчик публикует бизнес-ошибки в DLQ."""

        async def handler(message: dict) -> None:
            raise NotFoundError(detail="Not found")

        dlq_calls = []

        async def dlq_publisher(topic: str, message: dict) -> None:
            dlq_calls.append((topic, message))

        wrapped = wrap_handler(handler, "test.topic", dlq_publisher)
        await wrapped({})

        assert len(dlq_calls) == 1
        assert dlq_calls[0][1]["error_type"] == "NotFoundError"


class TestInMemoryProducerWithErrors:
    """Тесты InMemoryProducer с обработкой ошибок через safe_handle."""

    async def test_handler_error_does_not_crash_producer(self):
        """Ошибка в одном обработчике не влияет на другие."""
        from src.bus.in_memory.producer import InMemoryProducer

        bus = InMemoryProducer()
        received = []

        @bus.subscribe("test.topic")
        async def failing_handler(message: dict) -> None:
            raise ValueError("Ошибка")

        @bus.subscribe("test.topic")
        async def success_handler(message: dict) -> None:
            received.append(message)

        await bus.publish("test.topic", {"key": "value"})
        import asyncio

        await asyncio.sleep(0.05)

        # success_handler должен быть вызван, несмотря на ошибку в failing_handler
        assert len(received) == 1

    async def test_app_exception_in_handler_does_not_crash_producer(self):
        """AppException в обработчике не крашит продюсер."""
        from src.bus.in_memory.producer import InMemoryProducer

        bus = InMemoryProducer()

        @bus.subscribe("test.topic")
        async def handler(message: dict) -> None:
            raise NotFoundError(detail="Not found")

        # Не должно быть исключения
        await bus.publish("test.topic", {"id": 1})
        import asyncio

        await asyncio.sleep(0.05)
