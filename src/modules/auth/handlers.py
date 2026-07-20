"""
Обработчики событий модуля auth.

Модуль auth — чистый издатель: публикует события
(UserRegistered, UserLoggedIn, UserDeleted), но не
подписывается на события других модулей.

При необходимости side-effects на события auth
(например, отправка приветственного email) —
добавлять обработчики сюда.
"""

from src.bus.interface import MessageConsumer


def register_handlers(bus: MessageConsumer) -> None:
    """Регистрация обработчиков событий шины для auth."""
    # Пока пусто — модуль только публикует события
