"""Пользовательские сообщения сценариев подбора вакансий и подписок."""

WELCOME_MESSAGE = (
    "Добро пожаловать! Используйте /subscribe для подписки на предложения"
)
ALREADY_REGISTERED_MESSAGE = (
    "Вы уже зарегистрированы! /subscribe — подписаться на предложения"
)
REGISTRATION_REQUIRED_MESSAGE = "Сначала зарегистрируйтесь: /start"

SUBSCRIPTION_CHOOSE_CATEGORY_MESSAGE = (
    "Выберите категорию вакансий для подписки:"
)
SUBSCRIPTION_CHOOSE_CATEGORY_PAGE_TEMPLATE = (
    "Выберите категорию вакансий для подписки:\n\nСтраница {page} из {total_pages}"
)
SUBSCRIPTION_NO_CATEGORIES_MESSAGE = (
    "Сейчас нет доступных категорий для подписки"
)
SUBSCRIPTION_CATEGORY_UNAVAILABLE_MESSAGE = "Категория больше недоступна"
SUBSCRIPTION_CREATED_TEMPLATE = "Вы подписались на категорию «{category_name}»"
SUBSCRIPTION_CREATED_EDIT_TEMPLATE = (
    "✅ Вы подписались на категорию «{category_name}»\n\n"
    "Чтобы выбрать другую категорию, используйте /subscribe"
)
SUBSCRIPTION_CATEGORY_UNAVAILABLE_EDIT_MESSAGE = (
    "Категория больше недоступна.\n"
    "Используйте /subscribe, чтобы открыть актуальный список."
)
