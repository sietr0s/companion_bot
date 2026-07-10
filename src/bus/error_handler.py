"""
Единый обработчик ошибок для шины сообщений.

По аналогии с глобальным exception_handler в FastAPI:
- Ловит все исключения в обработчиках шины
- Логирует структурированно (topic, handler_name, message_preview)
- Для бизнес-исключений (AppException) — публикует в DLQ-топик
- Для CancelledError — корректно пробрасывает
- Для остальных — логирует traceback и публикует в DLQ
"""

import asyncio
import logging
import traceback
from collections.abc import Callable
from typing import Any

from src.core.exceptions import AppException

logger = logging.getLogger(__name__)

# Топик для сообщений, которые не удалось обработать
DLQ_TOPIC = "bus.dlq"


def _message_preview(message: dict[str, Any], max_len: int = 200) -> str:
    """Обрезать сообщение для логирования."""
    text = str(message)
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text


async def safe_handle(
    handler: Callable,
    topic: str,
    message: dict[str, Any],
    dlq_publisher: Callable | None = None,
) -> None:
    """
    Безопасно вызвать обработчик с обработкой всех исключений.

    Args:
        handler: Функция-обработчик (синхронная или асинхронная).
        topic: Топик, на который подписан обработчик.
        message: Сообщение для обработки.
        dlq_publisher: Функция для публикации в DLQ (опционально).
                       Должна принимать (topic, message).
    """
    handler_name = getattr(handler, "__name__", str(handler))
    msg_preview = _message_preview(message)

    try:
        if asyncio.iscoroutinefunction(handler):
            await handler(message)
        else:
            handler(message)

    except asyncio.CancelledError:
        logger.warning(
            "Обработчик %s отменён для топика '%s'",
            handler_name,
            topic,
        )
        raise

    except AppException as e:
        logger.warning(
            "Бизнес-ошибка в обработчике %s для топика '%s': %s (status=%s). "
            "Сообщение: %s",
            handler_name,
            topic,
            e.detail,
            e.status_code,
            msg_preview,
        )
        if dlq_publisher:
            await dlq_publisher(
                DLQ_TOPIC,
                {
                    "original_topic": topic,
                    "handler": handler_name,
                    "error_type": type(e).__name__,
                    "error_detail": e.detail,
                    "message": message,
                },
            )

    except (ConnectionError, TimeoutError) as e:
        logger.error(
            "Сетевая ошибка в обработчике %s для топика '%s': %s. "
            "Сообщение: %s",
            handler_name,
            topic,
            e,
            msg_preview,
        )
        if dlq_publisher:
            await dlq_publisher(
                DLQ_TOPIC,
                {
                    "original_topic": topic,
                    "handler": handler_name,
                    "error_type": type(e).__name__,
                    "error_detail": str(e),
                    "message": message,
                },
            )

    except Exception as e:
        tb = "".join(traceback.format_tb(e.__traceback__))
        logger.exception(
            "Неожиданная ошибка в обработчике %s для топика '%s': %s\n%s",
            handler_name,
            topic,
            e,
            tb,
        )
        if dlq_publisher:
            await dlq_publisher(
                DLQ_TOPIC,
                {
                    "original_topic": topic,
                    "handler": handler_name,
                    "error_type": type(e).__name__,
                    "error_detail": str(e),
                    "traceback": tb,
                    "message": message,
                },
            )


def wrap_handler(
    handler: Callable,
    topic: str,
    dlq_publisher: Callable | None = None,
) -> Callable:
    """
    Обернуть обработчик в безопасный вызов.

    Возвращает асинхронную функцию, которая вызывает handler
    через safe_handle. Удобно для декораторов.

    Args:
        handler: Функция-обработчик.
        topic: Топик, на который подписан обработчик.
        dlq_publisher: Функция для публикации в DLQ.

    Returns:
        Асинхронная функция-обёртка.
    """

    async def wrapper(message: dict[str, Any]) -> None:
        await safe_handle(handler, topic, message, dlq_publisher)

    wrapper.__name__ = handler.__name__
    wrapper.__qualname__ = handler.__qualname__
    wrapper.__module__ = handler.__module__
    wrapper.__doc__ = handler.__doc__

    return wrapper
