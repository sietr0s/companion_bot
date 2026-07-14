"""
SMTP-провайдер уведомлений.

Отправляет email через aiosmtplib.
Настройки берутся из core/config.py.
"""

import logging

from src.core.config import settings

logger = logging.getLogger(__name__)


class SmtpProvider:
    """
    SMTP-провайдер: отправка email через aiosmtplib.

    Использует настройки SMTP_HOST, SMTP_PORT и т.д.
    из конфигурации приложения.
    """

    async def start(self) -> None:
        """SMTP не требует явного запуска — заглушка."""
        pass

    async def stop(self) -> None:
        """SMTP не требует явной остановки — заглушка."""
        pass

    async def send(self, to: str, subject: str, body: str) -> None:
        """
        Отправить email через SMTP.

        В реальной отправке используется aiosmtplib.
        При отсутствии подключения — логируем и не падаем.
        """
        try:
            from email.mime.text import MIMEText

            import aiosmtplib
            from aiosmtplib import SMTPException

            message = MIMEText(body, "html")
            message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            message["To"] = to
            message["Subject"] = subject

            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USERNAME,
                password=settings.SMTP_PASSWORD,
                start_tls=settings.SMTP_USE_TLS,
            )
            logger.info("Email отправлен: to=%s, subject=%s", to, subject)
        except SMTPException as e:
            logger.error("SMTP ошибка при отправке email to=%s, subject=%s: %s", to, subject, e)
            raise
        except (ConnectionError, TimeoutError) as e:
            logger.error("Ошибка подключения к SMTP to=%s: %s", to, e)
            raise
        except (ValueError, TypeError) as e:
            logger.error("Ошибка валидации данных email to=%s: %s", to, e)
            raise
        except Exception as e:
            logger.exception(
                "Неожиданная ошибка отправки email to=%s, subject=%s: %s",
                to,
                subject,
                e,
            )
            raise
