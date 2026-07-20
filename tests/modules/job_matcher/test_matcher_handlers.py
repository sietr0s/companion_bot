"""
Тесты обработчиков модуля job_matcher.

Проверяют регистрацию обработчиков сервисов job_matcher.
"""

from src.modules.job_matcher.handlers import register_handlers


class TestHandlers:
    """Тесты обработчиков шины."""

    async def test_start_handler_registers(self):
        """
        register_handlers не падает.
        """
        # Не должно быть ошибки
        register_handlers()

    async def test_subscribe_handler_registers(self):
        """
        register_handlers не падает.
        """
        register_handlers()

    async def test_offer_handler_registers(self):
        """
        register_handlers не падает.
        """
        register_handlers()
