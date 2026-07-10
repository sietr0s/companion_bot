"""
Конфигурация топиков шины сообщений.

Единая точка определения всех топиков — исключает
хардкод строк в разных модулях и опечатки.
При добавлении нового события — добавляем топик сюда.
"""


class BusTopics:
    """Реестр топиков шины сообщений."""

    # Модуль Auth
    USER_REGISTERED: str = "user.registered"
    USER_LOGGED_IN: str = "user.logged_in"
    USER_DELETED: str = "user.deleted"

    # Модуль Users
    PROFILE_CREATED: str = "profile.created"
    PROFILE_UPDATED: str = "profile.updated"
    PROFILE_DELETED: str = "profile.deleted"

    # Модуль TelegramClients
    TG_MESSAGE_RECEIVED: str = "tg.message.received"
    TG_MESSAGE_SEND: str = "tg.message.send"
    TG_ACCOUNT_CONNECTED: str = "tg.account.connected"
    TG_ACCOUNT_DISCONNECTED: str = "tg.account.disconnected"

    # Модуль Notifications
    NOTIFICATION_SEND: str = "notification.send"

    # Модуль Media
    MEDIA_UPLOADED: str = "media.uploaded"
    MEDIA_DELETED: str = "media.deleted"

    # Модуль JobBot (шлюз Telegram)
    BOT_MESSAGE_INCOMING: str = "bot.message.incoming"
    BOT_MESSAGE_OUTGOING: str = "bot.message.outgoing"

    # Модуль JobMatcher (бизнес-логика)
    JOB_OFFER_PARSED: str = "job.offer.parsed"
    JOB_OFFER_CLASSIFIED: str = "job.offer.classified"
    SUBSCRIPTION_CREATED: str = "subscription.created"
    SUBSCRIPTION_UPDATED: str = "subscription.updated"
    SUBSCRIPTION_DELETED: str = "subscription.deleted"

    # Модуль Classifier
    TEXT_CLASSIFY_REQUEST: str = "text.classify.request"
    TEXT_CLASSIFY_COMPLETED: str = "text.classify.completed"
