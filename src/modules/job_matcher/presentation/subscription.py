"""Представление постраничного выбора категории подписки."""

from src.modules.job_matcher.constants import (
    SUBSCRIBE_CATEGORY_CALLBACK_PREFIX,
    SUBSCRIBE_PAGE_CALLBACK_PREFIX,
    SUBSCRIBE_PAGE_NOOP_CALLBACK,
)


def build_category_keyboard(
    categories: list[dict],
    page: int,
    total_pages: int,
) -> dict:
    """Построить inline-клавиатуру категорий и строку навигации."""
    rows = [
        [
            {
                "text": category["name"],
                "callback_data": (
                    f"{SUBSCRIBE_CATEGORY_CALLBACK_PREFIX}{category['id']}"
                ),
            }
        ]
        for category in categories
    ]
    previous_callback = (
        f"{SUBSCRIBE_PAGE_CALLBACK_PREFIX}{page - 1}"
        if page > 0
        else SUBSCRIBE_PAGE_NOOP_CALLBACK
    )
    next_callback = (
        f"{SUBSCRIBE_PAGE_CALLBACK_PREFIX}{page + 1}"
        if page + 1 < total_pages
        else SUBSCRIBE_PAGE_NOOP_CALLBACK
    )
    rows.append(
        [
            {"text": "← Назад", "callback_data": previous_callback},
            {"text": "Вперёд →", "callback_data": next_callback},
        ]
    )
    return {"inline_keyboard": rows}
