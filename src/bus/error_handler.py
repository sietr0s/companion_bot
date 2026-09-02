"""
Единый обработчик ошибок для шины сообщений.

По аналогии с глобальным exception_handler в FastAPI:
- Ловит все исключения в обработчиках шины
- Логирует структурированно (topic, handler_name, message_preview)
- Для CancelledError — корректно пробрасывает
"""

import asyncio
import logging
import traceback
from collections.abc import Callable
from typing import Any

from src.core.exceptions import AppException

logger = logging.getLogger(__name__)


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
) -> None:
    """
    Безопасно вызвать обработчик с обработкой всех исключений.

    Args:
        handler: Функция-обработчик (синхронная или асинхронная).
        topic: Топик, на который подписан обработчик.
        message: Сообщение для обработки.
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

    except (ConnectionError, TimeoutError) as e:
        logger.error(
            "Сетевая ошибка в обработчике %s для топика '%s': %s. "
            "Сообщение: %s",
            handler_name,
            topic,
            e,
            msg_preview,
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


def wrap_handler(
    handler: Callable,
    topic: str,
) -> Callable:
    """
    Обернуть обработчик в безопасный вызов.

    Возвращает асинхронную функцию, которая вызывает handler
    через safe_handle. Удобно для декораторов.

    Args:
        handler: Функция-обработчик.
        topic: Топик, на который подписан обработчик.

    Returns:
        Асинхронная функция-обёртка.
    """

    async def wrapper(message: dict[str, Any]) -> None:
        await safe_handle(handler, topic, message)

    wrapper.__name__ = handler.__name__
    wrapper.__qualname__ = handler.__qualname__
    wrapper.__module__ = handler.__module__
    wrapper.__doc__ = handler.__doc__

    return wrapper
