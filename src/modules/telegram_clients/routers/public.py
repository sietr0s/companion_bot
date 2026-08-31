"""Public API composition for the Telegram clients module."""

from fastapi import APIRouter

from src.base.routers import create_crud_router
from src.modules.telegram_clients.dependencies import (
    get_telegram_account_service,
    get_telegram_chat_state_service,
    get_telegram_settings_service,
)
from src.modules.telegram_clients.routers.public_accounts import (
    router as accounts_router,
)
from src.modules.telegram_clients.routers.public_auth import router as auth_router
from src.modules.telegram_clients.routers.public_settings import (
    router as settings_router,
)
from src.modules.telegram_clients.routers.public_whitelist import router as whitelist_router
from src.modules.telegram_clients.schemas.public import (
    AccountCreate,
    AccountRead,
    AccountUpdate,
    ChatStateCreate,
    ChatStateRead,
    ChatStateUpdate,
    TelegramSettingsCreate,
    TelegramSettingsRead,
    TelegramSettingsUpdate,
)

router = APIRouter(prefix="/api/v1/public/telegram", tags=["Telegram Clients"])
router.include_router(auth_router)
router.include_router(accounts_router)
router.include_router(settings_router)
router.include_router(whitelist_router)
router.include_router(
    create_crud_router(
        get_service=get_telegram_account_service,
        create_schema=AccountCreate,
        update_schema=AccountUpdate,
        response_schema=AccountRead,
        prefix="/accounts",
        tags=["Telegram Accounts"],
        entity_name="TelegramAccount",
    )
)
router.include_router(
    create_crud_router(
        get_service=get_telegram_settings_service,
        create_schema=TelegramSettingsCreate,
        update_schema=TelegramSettingsUpdate,
        response_schema=TelegramSettingsRead,
        prefix="/settings",
        tags=["Telegram Settings"],
        entity_name="TelegramSettings",
    )
)
router.include_router(
    create_crud_router(
        get_service=get_telegram_chat_state_service,
        create_schema=ChatStateCreate,
        update_schema=ChatStateUpdate,
        response_schema=ChatStateRead,
        prefix="/chat-states",
        tags=["Telegram Chat States"],
        entity_name="TelegramChatState",
    )
)
