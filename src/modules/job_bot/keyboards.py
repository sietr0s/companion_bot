"""
Клавиатуры для Telegram-бота.

Reply-клавиатура — главное меню.
Inline-клавиатура — контекстные действия (подписки, офферы).
"""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from src.modules.job_bot.texts import (
    CONFIRM_BUTTON_NO,
    CONFIRM_BUTTON_YES,
    MAIN_MENU_BUTTON_FIND_JOB,
    MAIN_MENU_BUTTON_MY_SUBSCRIPTIONS,
    MAIN_MENU_BUTTON_SETTINGS,
    MAIN_MENU_PLACEHOLDER,
    OFFER_BUTTON_DETAILS,
    OFFER_BUTTON_SUBSCRIBE_SIMILAR,
    SUBSCRIPTION_BUTTON_EDIT,
    SUBSCRIPTION_BUTTON_UNSUBSCRIBE,
)


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная Reply-клавиатура с основными командами."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MAIN_MENU_BUTTON_MY_SUBSCRIPTIONS)],
            [KeyboardButton(text=MAIN_MENU_BUTTON_FIND_JOB)],
            [KeyboardButton(text=MAIN_MENU_BUTTON_SETTINGS)],
        ],
        resize_keyboard=True,
        input_field_placeholder=MAIN_MENU_PLACEHOLDER,
    )


def get_subscription_inline_keyboard(
    subscription_id: str,
) -> InlineKeyboardMarkup:
    """Inline-клавиатура для управления подпиской."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=SUBSCRIPTION_BUTTON_EDIT,
                    callback_data=f"edit_sub:{subscription_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=SUBSCRIPTION_BUTTON_UNSUBSCRIBE,
                    callback_data=f"unsub:{subscription_id}",
                ),
            ],
        ]
    )


def get_offer_inline_keyboard(offer_id: str) -> InlineKeyboardMarkup:
    """Inline-клавиатура для предложения о работе."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=OFFER_BUTTON_DETAILS,
                    callback_data=f"offer:{offer_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=OFFER_BUTTON_SUBSCRIBE_SIMILAR,
                    callback_data=f"subscribe_similar:{offer_id}",
                ),
            ],
        ]
    )


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Inline-клавиатура подтверждения действия."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=CONFIRM_BUTTON_YES, callback_data="confirm"),
                InlineKeyboardButton(text=CONFIRM_BUTTON_NO, callback_data="cancel"),
            ],
        ]
    )
