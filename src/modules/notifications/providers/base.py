"""
Абстракция провайдера уведомлений.

NotificationProvider — Protocol, который реализуют
конкретные провайдеры (SMTP, SendGrid и т.д.).
"""

from typing import Protocol


class NotificationProvider(Protocol):
    """
    Интерфейс провайдера уведомлений.

    Каждый провайдер реализует метод send()
    и методы жизненного цикла start/stop.
    """

    async def send(self, to: str, subject: str, body: str) -> None: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
