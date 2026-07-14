"""
Сервисный слой для отправки сообщений через Telegram-бота.

Вынесен из handlers.py — бизнес-логика отправки,
а не только транспорт.
"""

import logging

from aiogram import Bot

from src.modules.job_bot.keyboards import get_main_keyboard
from src.modules.job_bot.texts import (
    VACANCY_LOCATION_TEMPLATE,
    VACANCY_SALARY_TEMPLATE,
    VACANCY_SALARY_UNKNOWN,
    VACANCY_TAGS_TEMPLATE,
)

logger = logging.getLogger(__name__)


class BotService:
    """
    Сервис для отправки сообщений через Telegram-бота.

    Используется обработчиками шины (bot.message.outgoing).
    """

    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send_message(
        self,
        chat_id: int,
        text: str,
        keyboard: dict | None = None,
    ) -> None:
        """
        Отправить сообщение пользователю.

        Если передан keyboard — добавляет клавиатуру к сообщению.
        Ошибки отправки логируются, но не пробрасываются наверх.
        """
        if not chat_id or not text:
            logger.warning("Неполные данные для отправки: chat_id=%s, text=%s", chat_id, text)
            return

        try:
            from aiogram.exceptions import TelegramNetworkError, TelegramServerError

            if keyboard:
                await self._bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=get_main_keyboard(),
                )
            else:
                await self._bot.send_message(
                    chat_id=chat_id,
                    text=text,
                )

            logger.info(
                "Сообщение отправлено в чат %s: %s",
                chat_id,
                text[:50],
            )
        except TelegramNetworkError as e:
            logger.error("Ошибка сети Telegram при отправке в чат %s: %s", chat_id, e)
        except TelegramServerError as e:
            logger.error("Ошибка сервера Telegram при отправке в чат %s: %s", chat_id, e)
        except (ValueError, TypeError) as e:
            logger.error("Ошибка валидации данных для отправки в чат %s: %s", chat_id, e)
        except Exception as e:
            logger.exception("Неожиданная ошибка при отправке сообщения в чат %s: %s", chat_id, e)

    async def send_offer(
        self,
        chat_id: int,
        title: str,
        description: str | None = None,
        tags: list[str] | None = None,
        salary_from: int | None = None,
        salary_to: int | None = None,
        location: str | None = None,
    ) -> None:
        """
        Отправить предложение о работе с клавиатурой.

        Форматирует сообщение и добавляет Inline-клавиатуру.
        """
        from src.modules.job_bot.keyboards import get_offer_inline_keyboard

        text_parts = [
            f"*{title}*",
        ]
        if description:
            text_parts.append(description)
        if salary_from or salary_to:
            salary_from_str = salary_from or VACANCY_SALARY_UNKNOWN
            salary_to_str = salary_to or VACANCY_SALARY_UNKNOWN
            salary = f"{salary_from_str} - {salary_to_str} ₽"
            text_parts.append(VACANCY_SALARY_TEMPLATE.format(salary=salary))
        if location:
            text_parts.append(VACANCY_LOCATION_TEMPLATE.format(location=location))
        if tags:
            text_parts.append(VACANCY_TAGS_TEMPLATE.format(tags=", ".join(tags[:5])))

        text = "\n\n".join(text_parts)

        await self._bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=get_offer_inline_keyboard(""),
        )
