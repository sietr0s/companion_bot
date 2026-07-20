"""
Обработчики событий шины для модуля media.

В MVP — пусто. Будущие side-effects:
- обработка входящих событий от других модулей
- генерация превью после загрузки
- репликация файлов
"""

from src.bus.interface import MessageConsumer


def register_handlers(bus: MessageConsumer) -> None:
    """Регистрация обработчиков событий шины для media."""
    # Пока пусто — модуль только публикует события
