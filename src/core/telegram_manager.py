"""
Фабрика для создания TelegramClientManager.

Этот модуль устраняет циклическую зависимость:
- Раньше: telegram_clients/dependencies.py → main.py → client_manager
- Теперь: telegram_clients/dependencies.py → core/telegram_manager.py
"""

import logging

from src.bus.interface import MessageBus
from src.modules.telegram_clients.client_manager import TelegramClientManager

logger = logging.getLogger(__name__)

# Глобальный экземпляр менеджера (singleton)
_telegram_client_manager: TelegramClientManager | None = None


def create_telegram_client_manager(message_bus: MessageBus) -> TelegramClientManager:
    """
    Создать или вернуть существующий TelegramClientManager.

    Args:
        message_bus: Шина сообщений для публикации входящих событий

    Returns:
        Singleton-экземпляр TelegramClientManager
    """
    global _telegram_client_manager
    if _telegram_client_manager is None:
        _telegram_client_manager = TelegramClientManager(message_bus=message_bus)
        logger.info("Создан новый экземпляр TelegramClientManager")
    return _telegram_client_manager


def get_telegram_client_manager() -> TelegramClientManager:
    """
    Получить существующий TelegramClientManager.

    Возвращает:
        TelegramClientManager: Глобальный экземпляр менеджера

    Raises:
        RuntimeError: Если менеджер ещё не создан
    """
    if _telegram_client_manager is None:
        raise RuntimeError(
            "TelegramClientManager ещё не создан. "
            "Вызовите create_telegram_client_manager() перед использованием."
        )
    return _telegram_client_manager


def reset_telegram_client_manager() -> None:
    """
    Сбросить глобальный экземпляр (для тестов).

    Не используйте в production-коде.
    """
    global _telegram_client_manager
    _telegram_client_manager = None
