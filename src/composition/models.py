"""Register module ORM models at the application composition boundary."""


def load_models() -> None:
    """Импортировать ORM-модели, чтобы они попали в Base.metadata."""
    from src.modules.auth.models import Auth  # noqa: F401
    from src.modules.batching.config.model import BatchingConfigModel  # noqa: F401
    from src.modules.behavior.models import BehaviorAccountState, BehaviorChatState  # noqa: F401
    from src.modules.instagram_clients.models import (  # noqa: F401
        InstagramAccount,
        InstagramChatState,
        InstagramSettings,
    )
    from src.modules.memory.models import (  # noqa: F401
        Conversation,
        Message,
        MessageBatch,
        SummaryState,
        VectorRecord,
    )
    from src.modules.telegram_clients.models import (  # noqa: F401
        TelegramAccount,
        TelegramChatState,
        TelegramSettings,
    )
    from src.modules.users.models import User  # noqa: F401
