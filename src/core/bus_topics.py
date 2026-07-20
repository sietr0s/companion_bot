"""
Конфигурация топиков шины сообщений.

Единая точка определения всех топиков — исключает
хардкод строк в разных модулях и опечатки.
При добавлении нового события — добавляем топик сюда.

Соглашение об именовании:
  - {module}.event.{domain_action}  — событие, которое публикует ВЛАДЕЛЕЦ модуля
    (в его домене что-то произошло). Другие модули могут подписаться и реагировать.
  - {module}.command.{action}       — команда, которую публикует НЕ владелец,
    чтобы попросить другой модуль что-то сделать (side-effect).
"""


class BusTopics:
    """Реестр топиков шины сообщений."""

    # ========== Events (публикует владелец модуля) ==========

    # Модуль Auth — события аутентификации
    USER_REGISTERED: str = "auth.event.user.registered"
    USER_LOGGED_IN: str = "auth.event.user.logged_in"
    USER_DELETED: str = "auth.event.user.deleted"

    # Модуль Users — события профилей
    PROFILE_CREATED: str = "users.event.profile.created"
    PROFILE_UPDATED: str = "users.event.profile.updated"
    PROFILE_DELETED: str = "users.event.profile.deleted"

    # Модуль TelegramClients — события Telegram-аккаунтов
    TG_MESSAGE_RECEIVED: str = "telegram_clients.event.message.received"
    TG_ACCOUNT_CONNECTED: str = "telegram_clients.event.account.connected"
    TG_ACCOUNT_DISCONNECTED: str = "telegram_clients.event.account.disconnected"

    # Модуль Media — события файлов
    MEDIA_UPLOADED: str = "media.event.uploaded"
    MEDIA_DELETED: str = "media.event.deleted"

    # Модуль JobBot — события входящих сообщений от бота
    BOT_MESSAGE_INCOMING: str = "job_bot.event.message.incoming"

    # Модуль JobMatcher — события бизнес-логики
    JOB_OFFER_PARSED: str = "job_matcher.event.offer.parsed"
    JOB_OFFER_CLASSIFIED: str = "job_matcher.event.offer.classified"
    SUBSCRIPTION_CREATED: str = "job_matcher.event.subscription.created"
    SUBSCRIPTION_UPDATED: str = "job_matcher.event.subscription.updated"
    SUBSCRIPTION_DELETED: str = "job_matcher.event.subscription.deleted"

    # Модуль Classifier — события классификации
    TEXT_CLASSIFY_COMPLETED: str = "classifier.event.classify.completed"

    # ========== Commands (публикует НЕ владелец, чтобы попросить другой модуль) ==========

    # Модуль TelegramClients — команды на отправку сообщений
    TG_MESSAGE_SEND: str = "telegram_clients.command.send_message"

    # Модуль Notifications — команда на отправку уведомления
    NOTIFICATION_SEND: str = "notifications.command.send"

    # Модуль Classifier — команда на классификацию текста
    TEXT_CLASSIFY_REQUEST: str = "classifier.command.classify"

    # Модуль JobBot — команда на отправку сообщения пользователю
    BOT_MESSAGE_OUTGOING: str = "job_bot.command.send_message"
    BOT_MESSAGE_EDIT: str = "job_bot.command.edit_message"

    # ========== Системные топики ==========
    DLQ: str = "bus.dlq"
